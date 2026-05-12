from abc import ABC, abstractmethod
from app.domain.entities.inbox_message import InboxMessage

class IInboxRepository(ABC):
    
    @abstractmethod
    async def exists_async(self, eventId: str, session = None) -> bool:
        pass

    @abstractmethod
    async def add_async(self, message: InboxMessage, session = None) -> None:
        pass
