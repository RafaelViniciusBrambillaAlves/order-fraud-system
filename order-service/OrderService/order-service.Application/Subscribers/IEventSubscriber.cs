namespace order_service.Application.Subscribers;

public interface IEventSubscriber
{
    void Subscribe(string queue, Func<ReadOnlyMemory<byte>, CancellationToken, Task> handler);
}
