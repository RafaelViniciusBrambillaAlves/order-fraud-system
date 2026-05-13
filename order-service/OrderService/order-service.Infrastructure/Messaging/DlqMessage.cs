namespace order_service.Infrastructure.Messaging;


// Encapsula uma mensagem que chegou na Dead Letter Queue
public sealed record DlqMessage(
    string MessageId,
    string EventType,
    string SourceQueue,
    string RoutingKey,
    string DeathReason, // Motivo pelo qual a mensagem foi rejeitada
    long DeathCount, // Quantas vezes essa mensagem foi rejeitada / expirou
    DateTimeOffset FirstDeathAt,
    ReadOnlyMemory<byte> Body // Corpo original da mensagem em bytes
); 
