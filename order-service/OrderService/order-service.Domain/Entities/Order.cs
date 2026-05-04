using order_service.Domain.Enums;

namespace order_service.Domain.Entities;

public class Order : EntityBase
{
    private Order() {}

    public Order(string description, decimal amount)
    {
        Description = description;
        Amount = amount;
        Status = OrderStatus.PENDING;
        CreatedAt = DateTime.UtcNow;
    }

    public string Description { get; private set; } = string.Empty;
    public decimal Amount { get; private set; }
    public OrderStatus Status { get; private set; }
    public DateTime CreatedAt { get; private set; }

    public void Approve()
    {
        if (Status != OrderStatus.PENDING)
        {
            throw new InvalidOperationException("Only pending orders can be approved.");
        }

        Status = OrderStatus.APPROVED;
    }

    public void Reject()
    {
        if (Status != OrderStatus.PENDING)
        {
            throw new InvalidOperationException("Only pending orders can be rejected.");
        }
        
        Status = OrderStatus.REJECTED;
    }

}
