from app.domain.repositories.order_repository_interface import IOrderRepository
from app.domain.entities.order import Order
from typing import List, Optional

class MongoOrderRepository(IOrderRepository):
    def __init__(self, db):
        self.collection = db.orders

    async def add(self, order: Order) -> None:
        order_data = order.model_dump(mode = "json")

        order_data['_id'] = order_data.pop('id')

        await self.collection.insert_one(order_data)


    async def get_by_id(self, id: str) -> Optional[Order]:
        doc = await self.collection.find_one({"_id": id})

        if doc:
            doc['id'] = doc.pop('_id')
            return Order(**doc)
        return None

    async def list_all(self) -> List[Order]:
        cursor = self.collection.find()
        orders = []

        for doc in await cursor.to_list(length = 100):
            doc['id'] = doc.pop('_id')
            orders.append(Order(**doc))

        return orders