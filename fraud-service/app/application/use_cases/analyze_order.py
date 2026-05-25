from app.schemas.order_created_event import OrderCreatedEvent
from app.domain.enums.fraud_status import FraudStatus

AMOUNT_THRESHOLD = 1000.0

def analyze_order(event: OrderCreatedEvent) -> str:

    if event.amount > AMOUNT_THRESHOLD:
        return FraudStatus.REJECTED
    
    return FraudStatus.APPROVED