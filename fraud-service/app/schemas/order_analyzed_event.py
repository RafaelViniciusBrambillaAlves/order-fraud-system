from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, timezone
from app.domain.enums.fraud_status import FraudStatus

class OrderAnalyzedEvent(BaseModel):
    order_id: UUID
    fraud_status: FraudStatus
    analyzed_at: datetime = Field(
        default_factory = lambda: datetime.now(timezone.utc)
        )
    
    model_config = {"use_enum_values": True}