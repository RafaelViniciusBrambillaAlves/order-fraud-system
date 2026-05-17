using System;
using order_service.Domain.Entities;

namespace order_service.Domain.Repositories;

public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<IEnumerable<Order>> GetAllAsync(CancellationToken cancellationToken = default);
    Task AddAsync(Order order, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<Order>> GetPendingTimedOutAsync(TimeSpan timeout, CancellationToken cancellationToken = default);

}
