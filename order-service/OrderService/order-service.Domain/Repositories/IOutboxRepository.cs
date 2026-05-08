using System;
using System.ComponentModel;
using order_service.Domain.Entities;

namespace order_service.Domain.Repositories;

public interface IOutboxRepository
{
    Task AddAsync(OutboxMessage message, CancellationToken ct = default);

    Task<IReadOnlyList<OutboxMessage>> GetPendingAsync(int limit = 50, CancellationToken ct = default);

    Task SaveChangesAsync(CancellationToken ct = default);
}
