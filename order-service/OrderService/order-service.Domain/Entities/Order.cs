using order_service.Domain.Enums;


namespace order_service.Domain.Entities;

public class Order : EntityBase
{
    public string Description { get; private set; } = string.Empty;
    public decimal Amount { get; private set; }
    public OrderStatus Status { get; private set; }
    public DateTime CreatedAt { get; private set; }
    public DateTime UpdatedAt { get; private set; }
    public DateTime? SagaStartedAt { get; private set; }
    public DateTime? SagaCompletedAt { get; private set; }

    private Order() {}

    public Order(
        string description, 
        decimal amount)
    {
        Description = description;
        Amount = amount;
        Status = OrderStatus.PENDING_FRAUD_CHECK;
        CreatedAt = DateTime.UtcNow;
        UpdatedAt = DateTime.UtcNow;
    }

    public void Approve()
    {
        if (Status != OrderStatus.PENDING_FRAUD_CHECK)
        {
            throw new InvalidOperationException("Only pending orders can be approved.");
        }

        Status = OrderStatus.APPROVED;
        UpdatedAt = DateTime.UtcNow;
    }

    public void Reject()
    {
        if (Status != OrderStatus.PENDING_FRAUD_CHECK)
        {
            throw new InvalidOperationException("Only pending orders can be rejected.");
        }
        
        Status = OrderStatus.REJECTED;
        UpdatedAt = DateTime.UtcNow;
    }

    public void UpdateStatus(OrderStatus newStatus)
    {   
        if (Status == OrderStatus.APPROVED || Status == OrderStatus.REJECTED)
            throw new InvalidOperationException(
                $"Cannot change status of an already finalized order. Current={Status}");

        Status = newStatus;
        UpdatedAt = DateTime.UtcNow;
    }  

    public void StartSaga()
    {
        if (SagaStartedAt.HasValue)
            throw new InvalidOperationException(
                $"Saga already started for Order {Id}.");

        SagaStartedAt = DateTime.UtcNow;
    }

    public void MarkAsTimedOut()
    {
        if (Status != OrderStatus.PENDING_FRAUD_CHECK)
            throw new InvalidOperationException(
                $"Cannot time out Order {Id}: current status is {Status}.");
            
        Status = OrderStatus.TIMED_OUT;
        SagaCompletedAt = DateTime.UtcNow;
    }

}
