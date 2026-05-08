from motor.motor_asyncio import AsyncIOMotorClient
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
