from app.domain.entities.entity_base import EntityBase
from app.domain.enums.fraud_status import FraudStatus
from uuid import UUID
from datetime import datetime, timezone
from pydantic import Field

class Order(EntityBase):
    order_id: UUID
    amount: float
    fraud_status: FraudStatus
    analyze_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

