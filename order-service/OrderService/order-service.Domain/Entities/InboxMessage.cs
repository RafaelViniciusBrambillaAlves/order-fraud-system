namespace order_service.Domain.Entities;

public class InboxMessage : EntityBase
{
    public string EventId { get; private set; } = string.Empty;
    public DateTime ProcessedAt { get; private set; }

    private InboxMessage() {}

    public InboxMessage(string eventId)
    {
        EventId = eventId;
        ProcessedAt = DateTime.UtcNow;
    }
}
