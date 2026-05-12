using System;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using order_service.Application.Publishers;
using order_service.Domain.Repositories;

namespace order_service.Infrastructure.Messaging;

public sealed class OutboxRelayWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IEventPublisher _publisher;
    private readonly ILogger<OutboxRelayWorker> _logger;

    // Intervalo entre cada ciclo
    private static readonly TimeSpan PollingInterval = TimeSpan.FromMilliseconds(500);

    public OutboxRelayWorker(
        IServiceScopeFactory scopeFactory,
        IEventPublisher publisher,
        ILogger<OutboxRelayWorker> logger)
    {
        _scopeFactory = scopeFactory;
        _publisher = publisher;
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

            await Task.Delay(PollingInterval, stoppingToken);
        }
    }

    private async Task ProcessBatchAsync(CancellationToken ct)
    {
        await using var scope = _scopeFactory.CreateAsyncScope();
        var outboxRepository = scope.ServiceProvider.GetRequiredService<IOutboxRepository>();

        var messages = await outboxRepository.GetPendingAsync(limit: 50, ct);

        if (messages.Count == 0)
            return;

        _logger.LogInformation(
            "OutboxRelay: processing {Count} pending message(s).", messages.Count);

        foreach (var message in messages)
        {
            try
            {
                await _publisher.PublishAsync(
                    message.Payload,
                    message.Exchange,
                    message.RoutingKey,
                    ct);
                
                message.MarkAsSent();

                _logger.LogInformation(
                     "Outbox message sent | Id={Id} EventType={EventType}",
                    message.Id, message.EventType);
                
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to publish outbox message | Id={Id} Attempt={Retry}",
                    message.Id, message.RetryCount + 1);
                
                message.MarkAsFailed(ex.Message);
            }
        }

        await outboxRepository.SaveChangesAsync(ct);
    }
}
