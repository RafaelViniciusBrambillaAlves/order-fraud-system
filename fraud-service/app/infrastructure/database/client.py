from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.settings import settings

class MongoDatabase:

    def __init__(self):
        self.client = AsyncIOMotorClient(
            settings.mongodb_url,
            uuidRepresentation = 'standard'
        )
        self.db = self.client[settings.mongodb_database]

    def get_database(self):
        return self.db
       
    async def close(self):
        self.client.close()

    @staticmethod
    async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:

        await db["outbox_messages"].create_index(
            [("status", 1), ("created_at", 1)],
            partialFilterExpression = {"status": 0},  
            name = "ix_outbox_pending",
        )
        await db["orders"].create_index(
            [("order_id", 1)],
            name = "ix_orders_order_id"
        )