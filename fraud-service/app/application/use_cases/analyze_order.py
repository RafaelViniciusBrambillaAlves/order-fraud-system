from app.schemas.order_created_event import OrderCreatedEvent
from app.domain.enums.fraud_status import FraudStatus

def analyze_order(event: OrderCreatedEvent) -> str:

    if event.amount > 1000:
        return FraudStatus.REJECTED
    
    return FraudStatus.APPROVED