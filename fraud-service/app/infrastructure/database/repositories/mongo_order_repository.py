"""
Repositório MongoDB para pedidos analisados pelo fraud-service.
"""
import logging

from app.domain.repositories.order_repository_interface import IOrderRepository
from app.domain.entities.order import Order
from typing import List, Optional, Any

logger = logging.getLogger(__name__)


class MongoOrderRepository(IOrderRepository):

    def __init__(self, db):
        self.collection = db.orders

    async def add_async(
        self, 
        order: Order,
        session: Any | None = None
    ) -> None:
        
        doc = order.model_dump(mode = "json")

        doc['_id'] = doc.pop('id')

        await self.collection.insert_one(doc, session = session)


    async def get_by_id(
        self, 
        id: str
    ) -> Optional[Order]:

        doc = await self.collection.find_one({"_id": id})

        if doc:
            doc['id'] = doc.pop('_id')
            return Order(**doc)
        return None

    async def list_all(self) -> List[Order]:
        docs = await self.collection.find().to_list(length = 100)
        orders = []
        
        for doc in docs:
            doc['id'] = doc.pop('_id')
            orders.append(Order(**doc))

        return orders