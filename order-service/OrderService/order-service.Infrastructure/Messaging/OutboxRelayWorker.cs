using System.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using order_service.Application.Publishers;
using order_service.Domain.Repositories;
using order_service.Application.Observability;
using OpenTelemetry.Trace;

namespace order_service.Infrastructure.Messaging;

public sealed class OutboxRelayWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<OutboxRelayWorker> _logger;

    // Intervalo entre cada ciclo
    private static readonly TimeSpan _interval = TimeSpan.FromMilliseconds(500);

    public OutboxRelayWorker(
        IServiceScopeFactory scopeFactory,
        ILogger<OutboxRelayWorker> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    protected override async Task ExecuteAsync (CancellationToken stoppingToken)
    {
        _logger.LogInformation("OutboxRelayWorker started");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await ProcessBatchAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                _logger.LogError(ex, "Unexpected error in OutboxRelayWorker cycle.");
            }

            await Task.Delay(_interval, stoppingToken);
        }
    }

    private async Task ProcessBatchAsync(CancellationToken cancellationToken)
    {
        await using var scope = _scopeFactory.CreateAsyncScope();

        var outboxRepository = scope.ServiceProvider.GetRequiredService<IOutboxRepository>();
        var orderRepository = scope.ServiceProvider.GetRequiredService<IOrderRepository>();
        var publisher = scope.ServiceProvider.GetRequiredService<IEventPublisher>();

        var pending = await outboxRepository.GetPendingAsync(limit: 50, cancellationToken);

        if (!pending.Any())
        {
            return;
        }

        using var cycleActivity = ApplicationTelemetry.ActivitySource.StartActivity(
            "outbox.relay.cycle", 
            ActivityKind.Internal);

        var sw = Stopwatch.StartNew(); 

        cycleActivity?.SetTag("outbox.batch.size", pending.Count());
        cycleActivity?.SetTag("outbox.pending_count", pending.Count());
        cycleActivity?.SetTag("outbox.event_types",
            string.Join(",", pending.Select(m => m.EventType).Distinct()));

        var published = 0;
        var failed = 0;

        foreach (var message in pending)
        {
            using var msgActivity = ApplicationTelemetry.ActivitySource.StartActivity(
                $"outbox.relay.publish {message.Exchange}/{message.RoutingKey}",
                ActivityKind.Producer); 

            msgActivity?.SetTag("outbox.message.id", message.Id.ToString());
            msgActivity?.SetTag("outbox.event_type", message.EventType);
            msgActivity?.SetTag("messaging.system", "rabbitmq");
            msgActivity?.SetTag("messaging.destination", message.Exchange);
            msgActivity?.SetTag("messaging.destination_kind", "exchange");  
            msgActivity?.SetTag("messaging.rabbitmq.routing_key", message.RoutingKey);
            msgActivity?.SetTag("messaging.operation", "publish");

            try
            {
                await publisher.PublishAsync(
                    message.Payload,
                    message.Exchange,
                    message.RoutingKey,
                    cancellationToken);
                
                message.MarkAsSent();

                if (message.RoutingKey == "order.created" && message.AggregateId.HasValue)
                {
                    var order = await orderRepository.GetByIdAsync(
                        message.AggregateId.Value,
                        cancellationToken);
                    
                    if (order is not null)
                    {
                        order.StartSaga();

                        msgActivity?.SetTag("saga.started", true);
                        msgActivity?.SetTag("order.id", order.Id.ToString());

                        _logger.LogInformation(
                            "Saga started | OrderId={OrderId} SagaStartedAt={SagaStartedAt}",
                            order.Id, DateTime.UtcNow);
                    }
                }

                await outboxRepository.SaveChangesAsync(cancellationToken);

                msgActivity?.SetStatus(ActivityStatusCode.Ok);

                published++;
                ApplicationTelemetry.OutboxMessagesPublished.Add(1,
                    new KeyValuePair<string, object?>("routing_key", message.RoutingKey));

                _logger.LogInformation(
                    "Outbox message published | MessageId={MessageId} Exchange={Exchange} RoutingKey={RoutingKey}",
                    message.Id, message.Exchange, message.RoutingKey);
                
            }
            catch (Exception ex)
            {
                failed++;

                msgActivity?.SetStatus(ActivityStatusCode.Error, ex.Message);
                msgActivity?.RecordException(ex);

                ApplicationTelemetry.OutboxMessagesFailed.Add(1,
                    new KeyValuePair<string, object?>("routing_key", message.RoutingKey));

                _logger.LogError(ex,
                    "Failed to publish outbox message | Id={Id} Attempt={Retry}",
                    message.Id, message.RetryCount + 1);
                
                message.MarkAsFailed(ex.Message);
            }
        }

        sw.Stop();

        await outboxRepository.SaveChangesAsync(cancellationToken);

        cycleActivity?.SetTag("outbox.batch.published", published);
        cycleActivity?.SetTag("outbox.batch.failed", failed);

        if (failed > 0)
        {
            cycleActivity?.SetStatus(ActivityStatusCode.Error, "All messages in batch failed");
        }
        else
        {
            cycleActivity?.SetStatus(ActivityStatusCode.Ok);
        }

        ApplicationTelemetry.OutboxRelayDuration.Record(sw.Elapsed.TotalSeconds);
    }
}
