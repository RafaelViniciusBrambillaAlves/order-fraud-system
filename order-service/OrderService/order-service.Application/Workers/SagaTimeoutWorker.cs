using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using order_service.Application.Services;
using order_service.Application.Settings;
using order_service.Domain.Repositories;

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
        await using var scope = _scopeFactory.CreateAsyncScope();

        var orderRepository = scope.ServiceProvider
            .GetRequiredService<IOrderRepository>();
        
        var timedOutOrders = await orderRepository.GetPendingTimedOutAsync(
            _settings.FraudAnalysisTimeout,
            cancellationToken);

        if (timedOutOrders.Count == 0)
        {
            _logger.LogDebug(
                "SagaTimeoutWorker: no timed-out orders found.");
            return;
        }

        _logger.LogWarning(
            "SagaTimeoutWorker: {Count} order(s) timed out. Processing...",
            timedOutOrders.Count);
        
        foreach (var order in timedOutOrders)
        {
            try
            {
                order.MarkAsTimedOut();

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
                _logger.LogInformation(ex,
                    "Order already processed, skipping timeout | OrderId={OrderId}",
                    order.Id);
            }
            catch (Exception ex)
            {
                 _logger.LogError(ex,
                    "Failed to expire order | OrderId={OrderId}",
                    order.Id);
            }
        }
    }
}
