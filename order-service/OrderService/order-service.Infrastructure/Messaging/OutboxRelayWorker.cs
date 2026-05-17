using System;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using order_service.Application.Publishers;
using order_service.Domain.Entities;
using order_service.Domain.Repositories;

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

        foreach (var message in pending)
        {
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

                        _logger.LogInformation(
                            "Saga started | OrderId={OrderId} SagaStartedAt={SagaStartedAt}",
                            order.Id, DateTime.UtcNow);
                    }
                }

                await outboxRepository.SaveChangesAsync(cancellationToken);

                _logger.LogInformation(
                    "Outbox message published | MessageId={MessageId} Exchange={Exchange} RoutingKey={RoutingKey}",
                    message.Id, message.Exchange, message.RoutingKey);
                
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to publish outbox message | Id={Id} Attempt={Retry}",
                    message.Id, message.RetryCount + 1);
                
                message.MarkAsFailed(ex.Message);
            }
        }

        await outboxRepository.SaveChangesAsync(cancellationToken);
    }
}
