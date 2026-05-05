from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.order import Order

class IOrderRepository(ABC):
    @abstractmethod
    async def add(self, order: Order) -> None:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Order]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Order]:
        pass


    