using System;
using order_service.Domain.Entities;
using order_service.Domain.Enums;
using order_service.Domain.Repositories;
using Microsoft.EntityFrameworkCore;

namespace order_service.Infrastructure.Persistence.Repositories;

public sealed class OutboxRepository : IOutboxRepository

{
    private readonly OrderDbContext _context;

    public OutboxRepository(OrderDbContext context)
    {
        _context = context;
    }

    public async Task AddAsync(OutboxMessage message, CancellationToken ct = default)
    {
        await _context.OutboxMessages.AddAsync(message, ct);
    }

    public async Task<IReadOnlyList<OutboxMessage>> GetPendingAsync(
        int limit = 50,
        CancellationToken ct = default)
    {
        return await _context.OutboxMessages
            .Where(m => m.Status == OutboxStatus.PENDING)
            .OrderBy(m => m.CreatedAt)
            .Take(limit)
            // .FromSql($"""
            //     SELECT TOP ({limit}) *
            //     FROM OutboxMessages WITH (UPDLOCK, READPAST)
            //     WHERE Status = 0
            //     ORDER BY CreatedAt
            //     """)
            .ToListAsync(ct);    
    }
    
    public Task SaveChangesAsync(CancellationToken ct = default)
    {
        return _context.SaveChangesAsync(ct);
    }
    
}
