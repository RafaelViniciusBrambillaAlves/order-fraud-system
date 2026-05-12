namespace order_service.Application.Subscribers;

// Metadados extraídos do header da mensagem recebida.
// Permite que handlers implementem idempotência via EventId
public sealed record MessageMetadata(
    string EventId,
    string EventType,
    string RoutingKey
);

public interface IEventSubscriber
{
    void Subscribe(string queue, Func<ReadOnlyMemory<byte>, MessageMetadata, CancellationToken, Task> handler);
                                 
}
