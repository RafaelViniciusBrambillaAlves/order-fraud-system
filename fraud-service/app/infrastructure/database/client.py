from motor.motor_asyncio import AsyncIOMotorClient

class MongoDatabase:

    def __init__(self):
        self.client = AsyncIOMotorClient(
            'mongodb://mongodb:27017',
            uuidRepresentation = 'standard'
        )
        self.db = self.client['fraud_db']

    def get_database(self):
        return self.db
       
    async def close(self):
        self.client.close()
