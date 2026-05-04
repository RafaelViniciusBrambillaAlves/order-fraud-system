using order_service.Domain.Enums;
using order_service.Domain.Entities;

namespace order_service.Application.ViewModels;

public class OrderViewModel
{
    public Guid Id { get; set; }
    public string Description { get; set; } = string.Empty;
    public decimal Amount { get; set; }
    public string Status { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }

    public static OrderViewModel FromEntity(Order order) => new()
    {
        Id = order.Id,
        Description = order.Description,
        Amount = order.Amount,
        Status = order.Status.ToString(),
        CreatedAt = order.CreatedAt
    };
}
