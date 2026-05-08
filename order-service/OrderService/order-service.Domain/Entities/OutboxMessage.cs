using order_service.Domain.Enums;

namespace order_service.Domain.Entities;

public sealed class OutboxMessage : EntityBase
{
    public string EventType { get; private set; }
    public string Payload { get; private set; }
    public string Exchange { get; private set; }
    public string RoutingKey { get; private set; }
    public OutboxStatus Status { get; private set; }
    public DateTime CreatedAt { get; private set; }
    public DateTime? SentAt { get; private set; }
    public int RetryCount { get; private set; }
    public string? LastError { get; private set; }  
    
    private OutboxMessage() {}

    public OutboxMessage(
        string eventType,
        string payload,
        string exchange,
        string routingKey)
    {
        EventType = eventType;
        Payload = payload;
        Exchange = exchange;
        RoutingKey = routingKey;
        Status = OutboxStatus.PENDING;
        CreatedAt = DateTime.UtcNow;
    }

    public void MarkAsSent()
    {
        Status = OutboxStatus.SENT;
        SentAt = DateTime.UtcNow;
    }

    public void MarkAsFailed(string error)
    {
        RetryCount ++;
        LastError = error;

        if (RetryCount >= 5)
            Status = OutboxStatus.Failed;
    }
}
