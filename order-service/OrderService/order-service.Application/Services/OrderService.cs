using order_service.Application.InputModels;
using order_service.Application.ViewModels;
using order_service.Domain.Entities;
using order_service.Domain.Repositories;
using order_service.Application.Events;
using order_service.Application.Publishers;
using System.Text.Json;
using System.ComponentModel;
using Microsoft.Extensions.Logging;

namespace order_service.Application.Services;

public class OrderService : IOrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly IOutboxRepository  _outboxRepository;
    public readonly ILogger<OrderService> _logger;
    private const string OrderEventsExchange  = "order.events";
    private const string OrderCreatedRoutingKey = "order.created";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public OrderService(
        IOrderRepository orderRepository, 
        IOutboxRepository  outboxRepository,
        ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _outboxRepository = outboxRepository;
        _logger = logger;
    }

    public async Task<OrderViewModel> CreateAsync(
        CreateOrderInputModel input, 
        CancellationToken cancellationToken = default)
    {
        var order = new Order(input.Description, input.Amount);

        var @event = new OrderCreatedEvent(
            EventId: Guid.NewGuid(),
            OrderId: order.Id, 
            Amount:order.Amount,
            CreatedAt: DateTime.UtcNow);    

        var outboxMessage = new OutboxMessage(
            aggregateId: order.Id,
            eventType: nameof(OrderCreatedEvent),
            payload: JsonSerializer.Serialize(@event, JsonOptions),
            exchange: OrderEventsExchange,
            routingKey: OrderCreatedRoutingKey);

        // Transação atomica: order + outbox ou nada
        await _orderRepository.AddAsync(order, cancellationToken);
        await _outboxRepository.AddAsync(outboxMessage, cancellationToken);
        await _orderRepository.SaveChangesAsync(cancellationToken); 

        return OrderViewModel.FromEntity(order);
    }

    public async Task<OrderViewModel?> GetByIdAsync(
        Guid id, 
        CancellationToken cancellationToken = default)
    {
        var order = await _orderRepository.GetByIdAsync(id, cancellationToken);

        return order is null ? null: OrderViewModel.FromEntity(order);
    }

    public async Task<IEnumerable<OrderViewModel>> GetAllAsync(
        CancellationToken cancellationToken = default)
    {
        var orders = await _orderRepository.GetAllAsync(cancellationToken);

        return orders.Select(OrderViewModel.FromEntity);
    }
}
