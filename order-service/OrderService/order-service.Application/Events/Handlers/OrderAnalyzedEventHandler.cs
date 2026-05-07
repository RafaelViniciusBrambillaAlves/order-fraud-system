using System;
using Microsoft.Extensions.Logging;
using order_service.Application.Events;
using order_service.Domain.Entities;
using order_service.Domain.Enums;
using order_service.Domain.Repositories;

namespace order_service.Application.Handlers;

public sealed class OrderAnalyzedEventHandler
{
    private readonly IOrderRepository _orderRepository;
    private readonly ILogger<OrderAnalyzedEventHandler> _logger;

    public OrderAnalyzedEventHandler(
        IOrderRepository orderRepository,
        ILogger<OrderAnalyzedEventHandler> logger
    )
    {
        _orderRepository = orderRepository;
        _logger = logger;
    }

    public async Task HandleAsync(
        OrderAnalyzedEvent @event,
        CancellationToken cancellationToken = default
    )
    {
        _logger.LogInformation(
            "Handling OrderAnalyzedEvent | OrderId={OrderId} FraudStatus={FraudStatus}",
            @event.OrderId, @event.FraudStatus
        );

        var order = await _orderRepository.GetByIdAsync(@event.OrderId, cancellationToken);

        if (order is null)
        {
            _logger.LogWarning(
                "Order not found for result event | OrderId={OrderId}",
                @event.OrderId
            );
            return;
        }

        if (string.IsNullOrWhiteSpace(@event.FraudStatus))
        {
             _logger.LogWarning(
            "FraudStatus is null or empty | OrderId={OrderId}",
            @event.OrderId);

            return;
        }

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

        await _orderRepository.SaveChangesAsync(cancellationToken);

        _logger.LogInformation(
            "Order status updated | OrderId={OrderId} NewStatus={NewStatus}",
            order.Id, newStatus
        );
    }
}
