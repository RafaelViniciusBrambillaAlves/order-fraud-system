using Microsoft.Extensions.Logging;
using order_service.Application.Events;
using order_service.Domain.Entities;
using order_service.Domain.Enums;
using order_service.Domain.Repositories;
using order_service.Application.Observability;
using System.Diagnostics;
using OpenTelemetry.Trace;
using System.Linq.Expressions;

namespace order_service.Application.Handlers;


/// <summary>
/// Processa o evento OrderAnalyzedEvent publicado pelo fraud-service.
///
/// Inbox Pattern:
///   1. Verifica se o EventId já foi processado (idempotência via InboxMessage).
///   2. Executa a lógica de negócio (atualiza status do pedido).
///   3. Persiste InboxMessage + Order na mesma transação EF Core.
///      Se qualquer etapa falhar, nenhuma alteração é commitada.
/// </summary>  
public sealed class OrderAnalyzedEventHandler
{
    private readonly IOrderRepository _orderRepository;
    private readonly IInboxRepository _inboxRepository;
    private readonly ILogger<OrderAnalyzedEventHandler> _logger;

    public OrderAnalyzedEventHandler(
        IOrderRepository orderRepository,
        IInboxRepository inboxRepository,
        ILogger<OrderAnalyzedEventHandler> logger
    )
    {
        _orderRepository = orderRepository;
        _inboxRepository = inboxRepository;
        _logger = logger;
    }

    public async Task HandleAsync(
        OrderAnalyzedEvent @event,
        string eventId,
        CancellationToken cancellationToken = default
    )
    {   
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            "handler.order.analyzed", 
            ActivityKind.Internal);

        activity?.SetTag("event.id", eventId);
        activity?.SetTag("order.id", @event.OrderId.ToString());
        activity?.SetTag("fraud.status", @event.FraudStatus);

        var sw = Stopwatch.StartNew();

        try
        {
            // Idempotencia 
            // Verifica se esse EventId ja foi processado.
            // Se sim - ignora silenciosamente
            var alreadyProcessed = await _inboxRepository
                .ExistsAsync(eventId, cancellationToken);

            if (alreadyProcessed)
            {
                activity?.SetTag("hanler.duplicate", "true");
                activity?.SetStatus(ActivityStatusCode.Ok);

                _logger.LogWarning(
                    "Duplicate event ignored | EventId={EventId} OrderId={OrderId}",
                    eventId, @event.OrderId);
                
                return;
            }

            _logger.LogInformation(
                "Handling OrderAnalyzedEvent | OrderId={OrderId} FraudStatus={FraudStatus}",
                @event.OrderId, @event.FraudStatus
            );

            // Busca do pedido    
            var order = await _orderRepository.GetByIdAsync(@event.OrderId, cancellationToken);

            if (order is null)
            {
                _logger.LogWarning(
                    "Order not found for result event | OrderId={OrderId}",
                    @event.OrderId
                );

                activity?.SetTag("order.found", false);
                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }

            activity?.SetTag("order.found", true);
            activity?.SetTag("order.current_status", order.Status.ToString());

            if (order.Status == OrderStatus.TIMED_OUT)
            {
                activity?.SetTag("handler.late_response", true);
                activity?.SetStatus(ActivityStatusCode.Ok);

                _logger.LogWarning(
                    "Late fraud response ignored — order already timed out | " +
                    "OrderId={OrderId} EventId={EventId} FraudStatus={FraudStatus}",
                    @event.OrderId, eventId, @event.FraudStatus);

                return;
            }

            if (string.IsNullOrWhiteSpace(@event.FraudStatus))
            {
                _logger.LogWarning(
                    "FraudStatus is null or empty | OrderId={OrderId} EventId={EventId}",
                    @event.OrderId, eventId);

                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }

            // Atualiza status do pedido
            var newStatus = @event.FraudStatus.ToLowerInvariant() switch
            {
                "approved" => OrderStatus.APPROVED,
                "rejected" => OrderStatus.REJECTED,
                _ => throw new ArgumentOutOfRangeException(
                    nameof(@event.FraudStatus),
                    $"Unknown fraud status: '{@event.FraudStatus}'")
            };

            // order.Approve();
            order.UpdateStatus(newStatus);

            // Persiste InboxMessage + Order na mesma transação 
            // se qualquer um dos SaveChanges falhar, nenhuma alteração é commitada
            await _inboxRepository.AddAsync(new InboxMessage(eventId), cancellationToken);

            // Um único SaveChanges salva Order + InboxMessage
            await _inboxRepository.SaveChangesAsync(cancellationToken);

            sw.Stop();

            activity?.SetTag("order.new_status", newStatus.ToString());
            activity?.SetTag("handler.duration_ms", sw.Elapsed.TotalMilliseconds); 
            activity?.SetTag("handler.outcome", "processed");
            activity?.SetStatus(ActivityStatusCode.Ok);

            if (order.SagaStartedAt.HasValue)
            {
                var sagaDuration = DateTime.UtcNow - order.SagaStartedAt.Value;

                ApplicationTelemetry.SagaDuration.Record(
                    sagaDuration.TotalSeconds,
                    new KeyValuePair<string, object?>("result", newStatus.ToString()));

                activity?.SetTag("saga.duration.seconds", sagaDuration.TotalSeconds);

                _logger.LogInformation(
                    "Saga concluída | OrderId={OrderId} NewStatus={NewStatus} " +
                    "EventId={EventId} SagaDurationSeconds={SagaDurationSeconds:F2} " +
                    "HandlerDurationMs={HandlerDurationMs:F1}",
                    order.Id, newStatus, eventId,
                    sagaDuration.TotalSeconds,
                    sw.Elapsed.TotalMilliseconds);
            }
            else
            {
                _logger.LogInformation(
                    "Status do pedido atualizado | OrderId={OrderId} NewStatus={NewStatus} " +
                    "EventId={EventId} HandlerDurationMs={HandlerDurationMs:F1}",
                    order.Id, newStatus, eventId,
                    sw.Elapsed.TotalMilliseconds);
            }

            ApplicationTelemetry.OrdersFinalized.Add(1,
                new KeyValuePair<string, object?>(
                    "status",
                    newStatus.ToString()));

        }
        catch (Exception ex)
        {
            sw.Stop();

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1,
                new KeyValuePair<string, object?>("operation", "handler.analyzed.handler"));

            _logger.LogError(ex,
                "Failed processing OrderAnalyzedEvent | " +
                "OrderId={OrderId} EventId={EventId} DurationMs={DurationMs:F1}",
                @event.OrderId,
                eventId,
                sw.Elapsed.TotalMilliseconds);

            throw;
        }
    }
}
