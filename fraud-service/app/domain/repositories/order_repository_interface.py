from abc import ABC, abstractmethod
from typing import List, Optional, Any
from app.domain.entities.order import Order

class IOrderRepository(ABC):
    @abstractmethod
    async def add_async(
        self, 
        order: Order,
        session: Any | None = None) -> None:
        pass
    
    @abstractmethod
    async def get_by_id(
        self, 
        id: str
    ) -> Optional[Order]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Order]:
        pass


    