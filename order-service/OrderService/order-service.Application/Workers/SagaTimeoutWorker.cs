using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using order_service.Application.Settings;
using order_service.Domain.Repositories;
using order_service.Application.Observability;
using System.Diagnostics;
using OpenTelemetry.Trace;

namespace order_service.Application.Workers;

/// Worker responsável por detectar e encerrar Sagas que excederam o timeout.
///
/// Problema que resolve:
///   O order-service publica um OrderCreatedEvent e aguarda um
///   OrderAnalyzedEvent do fraud-service. Se o fraud-service cair,
///   travar ou nunca responder, o pedido fica PENDING para sempre.
///   Este worker varre o banco periodicamente e expira esses pedidos.
///
/// Estratégia:
///   A cada CheckInterval, busca pedidos com:
///     Status = PENDING
///     SagaStartedAt <= UtcNow - FraudAnalysisTimeout
///   Para cada um, chama order.MarkAsTimedOut() e persiste.
///
/// Idempotência:
///   MarkAsTimedOut() lança InvalidOperationException se o status
///   não for PENDING - pedidos já aprovados/rejeitados/expirados são
///   ignorados silenciosamente.
public sealed class SagaTimeoutWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly SagaTimeoutSettings _settings;
    private readonly ILogger<SagaTimeoutWorker> _logger;

    public SagaTimeoutWorker(
        IServiceScopeFactory scopeFactory,
        IOptions<SagaTimeoutSettings> settings,
        ILogger<SagaTimeoutWorker> logger)
    {
        _scopeFactory = scopeFactory;
        _settings = settings.Value;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation(
            "SagaTimeoutWorker started | Timeout={Timeout} CheckInterval={Interval}",
            _settings.FraudAnalysisTimeout,
            _settings.CheckInterval);

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                await CheckAndExpireAsync(cancellationToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                _logger.LogError(ex, "SagaTimeoutWorker encountered an error during check cycle.");
            } 

            await Task.Delay(_settings.CheckInterval, cancellationToken);
        }
    }

    private async Task CheckAndExpireAsync(CancellationToken cancellationToken)
    {   
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            "saga.timeout.check", 
            ActivityKind.Internal);

        var sw = Stopwatch.StartNew();

        await using var scope = _scopeFactory.CreateAsyncScope();

        var orderRepository = scope.ServiceProvider
            .GetRequiredService<IOrderRepository>();
        
        try
        {
            var timedOutOrders = await orderRepository.GetPendingTimedOutAsync(
                _settings.FraudAnalysisTimeout,
                cancellationToken);

            if (timedOutOrders.Count == 0)
            {
                _logger.LogDebug(
                    "SagaTimeoutWorker: no timed-out orders found.");

                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }

            _logger.LogWarning(
                "SagaTimeoutWorker: {Count} order(s) timed out. Processing...",
                timedOutOrders.Count);
            
            var count = 0;

            foreach (var order in timedOutOrders)
            {   
                using var orderActivity = ApplicationTelemetry.ActivitySource.StartActivity(
                    "saga.timeout.cancel",
                    ActivityKind.Internal);

                orderActivity?.SetTag("order.id", order.Id.ToString());
                orderActivity?.SetTag("order.status", order.Status.ToString());
                orderActivity?.SetTag("saga.timeout.seconds", _settings.FraudAnalysisTimeout.TotalSeconds);
                orderActivity?.SetTag("saga.started_at", order.SagaStartedAt?.ToString("O"));

                try
                {
                    order.MarkAsTimedOut();

                    count++; 

                    ApplicationTelemetry.SagaTimeouts.Add(1,
                    new KeyValuePair<string, object?>("reason", "timeout"));

                    await orderRepository.SaveChangesAsync(cancellationToken);

                    _logger.LogWarning(
                        "Order saga timed out | " +
                        "OrderId={OrderId} " +
                        "SagaStartedAt={SagaStartedAt} " +
                        "Timeout={Timeout}",
                        order.Id,
                        order.SagaStartedAt,
                        _settings.FraudAnalysisTimeout);
                }
                catch (InvalidOperationException ex)
                {
                    orderActivity?.SetStatus(ActivityStatusCode.Ok);

                    _logger.LogInformation(ex,
                        "Order already processed, skipping timeout | OrderId={OrderId}",
                        order.Id);
                }
                catch (Exception ex)
                {
                    orderActivity?.SetStatus(ActivityStatusCode.Error, ex.Message);
                    orderActivity?.RecordException(ex);

                    _logger.LogError(ex,
                        "Failed to expire order | OrderId={OrderId}",
                        order.Id);
                }

                sw.Stop();

                activity?.SetTag("saga.timeout.cancelled_count", count);
                activity?.SetStatus(ActivityStatusCode.Ok);

                ApplicationTelemetry.SagaTimeoutCheckDuration.Record(
                    sw.Elapsed.TotalSeconds,
                    new KeyValuePair<string, object?>("cancelled", count));

            }
        }
        catch (Exception ex)
        {
            sw.Stop();

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1,
                new KeyValuePair<string, object?>("operation", "saga.timeout.check"));

            throw;
        }
    }
}
