from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.domain.entities.entity_base import EntityBase
from app.domain.enums.outbox_status import OutboxStatus

class OutboxMessage(EntityBase):
    id: UUID 
    event_type: str
    payload: str
    exchange: str
    routing_key: str
    status: OutboxStatus    
    created_at: datetime
    sent_at: Optional[datetime]
    retry_count: int
    last_error: Optional[str]

    # permite chamar métodos mutadores
    model_config = {"frozen": False} 

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: str,
        exchange: str,
        routing_key: str
    ) -> "OutboxMessage":
        return cls(
            id = uuid4(),
            event_type = event_type,
            payload = payload,
            exchange = exchange,
            routing_key = routing_key,
            status = OutboxStatus.PENDING,
            created_at = datetime.now(timezone.utc),
            sent_at = None,
            retry_count = 0,
            last_error = None
        )
    
    def mark_as_sent(self) -> None:
        self.status = OutboxStatus.SENT
        self.sent_at = datetime.now(timezone.utc)
    
    def mark_as_failed(self, error: str, max_retries: int = 5) -> None:
        self.retry_count += 1
        self.last_error = error

        if self.retry_count >= max_retries:
            self.status = OutboxStatus.FAILED
