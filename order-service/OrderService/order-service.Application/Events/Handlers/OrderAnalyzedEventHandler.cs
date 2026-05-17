using System;
using System.ComponentModel;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging;
using order_service.Application.Events;
using order_service.Domain.Entities;
using order_service.Domain.Enums;
using order_service.Domain.Repositories;

namespace order_service.Application.Handlers;


/// Processa o evento OrderAnalyzedEvent publicado pelo fraud-service.
///
/// Inbox Pattern:
///   1. Verifica se o EventId já foi processado (idempotência).
///   2. Executa a lógica de negócio.
///   3. Persiste o InboxMessage e salva tudo na mesma transação
///      — se qualquer passo falhar, nada é commitado.
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
        // Idempotencia 
        // Verifica se esse EventId ja foi processado.
        // Se sim - ignora silenciosamente
        var alreadyProcessed = await _inboxRepository
            .ExistsAsync(eventId, cancellationToken);

        if (alreadyProcessed)
        {
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

            return;
        }

        if (order.Status == OrderStatus.TIMED_OUT)
        {
            _logger.LogWarning(
                "Late fraud response ignored — order already timed out | " +
                "OrderId={OrderId} EventId={EventId} FraudStatus={FraudStatus}",
                @event.OrderId, eventId, @event.FraudStatus);
            return;
        }

        if (string.IsNullOrWhiteSpace(@event.FraudStatus))
        {
             _logger.LogWarning(
            "FraudStatus is null or empty | OrderId={OrderId}",
            @event.OrderId);

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

        _logger.LogInformation(
            "Order status updated | OrderId={OrderId} NewStatus={NewStatus} EventId={EventId}",
            order.Id, newStatus, eventId);
    }
}
