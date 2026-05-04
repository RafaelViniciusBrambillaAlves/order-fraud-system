using order_service.Application.InputModels;
using order_service.Application.ViewModels;

namespace order_service.Application.Services;

public interface IOrderService
{
    Task<OrderViewModel> CreateAsync(CreateOrderInputModel input, CancellationToken cancellationToken = default);
    Task<OrderViewModel?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<IEnumerable<OrderViewModel>> GetAllAsync(CancellationToken cancellationToken = default);   

}
