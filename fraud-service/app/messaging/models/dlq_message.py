from dataclasses import dataclass
from datetime import datetime 

@dataclass(slots = True)
class DlqMessage:
    message_id: str
    event_type: str
    source_queue: str
    routing_key: str
    death_reason: str
    death_count: int
    first_death: datetime
    body: str