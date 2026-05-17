
namespace order_service.Domain.Enums;

public enum OrderStatus
{
    PENDING_FRAUD_CHECK = 1,
    APPROVED = 2,
    REJECTED = 3,
    TIMED_OUT = 4
}
