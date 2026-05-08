using System;

namespace order_service.Application.Publishers;

public interface IEventPublisher
{
    Task PublishAsync<TEvent>(
        TEvent @event, 
        string exchange,
        string routingKey,
        CancellationToken cancellationToken = default)
        where TEvent : class;

    Task PublishAsync(
        string payload,
        string exchange,
        string routingKey,
        CancellationToken cancellationToken = default);

}
