from abc import ABC, abstractmethod
from app.schemas.order_analyzed_event import OrderAnalyzedEvent


class IOrderAnalyzedPublisher(ABC):

    @abstractmethod
    async def connect(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def close(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def publish(self, event: OrderAnalyzedEvent) -> None:
        raise NotImplemented