from app.domain.entities.entity_base import EntityBase
from datetime import datetime, timezone
from uuid import uuid4

class InboxMessage(EntityBase):
    event_id: str
    processed_at: datetime

    @classmethod
    def create(
        cls,
        event_id: str,
    ) -> "InboxMessage":
        return cls(
            event_id = event_id,
            processed_at = datetime.now(timezone.utc)
        )
        
