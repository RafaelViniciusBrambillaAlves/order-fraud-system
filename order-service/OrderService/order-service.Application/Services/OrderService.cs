using order_service.Application.InputModels;
using order_service.Application.ViewModels;
using order_service.Domain.Entities;
using order_service.Domain.Repositories;
using order_service.Application.Events;
using order_service.Application.Publishers;

namespace order_service.Application.Services;

public class OrderService : IOrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly IEventPublisher _eventPublisher;

    private const string OrderEventsExchange  = "order.events";
    private const string OrderCreatedRoutingKey = "order.created";

    public OrderService(
        IOrderRepository orderRepository, 
        IEventPublisher eventPublisher)
    {
        _orderRepository = orderRepository;
        _eventPublisher = eventPublisher;
    }

    public async Task<OrderViewModel> CreateAsync(
        CreateOrderInputModel input, 
        CancellationToken cancellationToken = default)
    {
        var order = new Order(input.Description, input.Amount);

        await _orderRepository.AddAsync(order, cancellationToken);
        await _orderRepository.SaveChangesAsync(cancellationToken);

        var @event = new OrderCreatedEvent(
            OrderId: order.Id, 
            Description: order.Description, 
            Amount:order.Amount,
            CreatedAt: DateTime.UtcNow);

        await _eventPublisher.PublishAsync(
            @event,
            exchange: OrderEventsExchange,
            routingKey: OrderCreatedRoutingKey,
            cancellationToken: cancellationToken);

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
