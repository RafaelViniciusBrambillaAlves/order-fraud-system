using Microsoft.EntityFrameworkCore;
using order_service.Domain.Entities;
using order_service.Domain.Repositories;

namespace order_service.Infrastructure.Persistence.Repositories;

public class InboxRepository : IInboxRepository
{
    private readonly OrderDbContext _context;

    public InboxRepository(OrderDbContext context)
    {
        _context = context;
    }

    public async Task<bool> ExistsAsync(
        string eventId,
        CancellationToken ct)
    {
        return await _context.InboxMessages
            .AnyAsync(x => x.EventId == eventId, ct);
    }

    public async Task AddAsync(
        InboxMessage message,
        CancellationToken ct)
    {
        await _context.InboxMessages.AddAsync(message, ct);
    }

    public async Task SaveChangesAsync(CancellationToken ct)
    {
        await _context.SaveChangesAsync(ct);
    }
}
