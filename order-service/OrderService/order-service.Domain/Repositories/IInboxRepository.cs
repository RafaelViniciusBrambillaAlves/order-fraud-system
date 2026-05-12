using order_service.Domain.Entities;

namespace order_service.Domain.Repositories;

public interface IInboxRepository
{
    Task<bool> ExistsAsync(string eventId, CancellationToken ct);
    Task AddAsync(InboxMessage message, CancellationToken ct);
    Task SaveChangesAsync(CancellationToken ct);
}
