from abc import ABC, abstractmethod
from app.domain.entities.outbox_message import OutboxMessage
from typing import List, Any

class IOutboxMessageRepository(ABC):
    
    @abstractmethod
    async def add_async(
        self, 
        message: OutboxMessage,
        session: Any | None = None
    ) -> None:
        pass

    @abstractmethod
    async def get_pending_async(
        self, 
        limit: int = 50
    ) -> List[OutboxMessage]:
        pass

    @abstractmethod
    async def save_async(
        self, 
        message: OutboxMessage
    ) -> None:
        pass