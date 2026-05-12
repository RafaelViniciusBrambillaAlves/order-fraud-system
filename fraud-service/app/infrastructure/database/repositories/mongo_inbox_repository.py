from motor.motor_asyncio import AsyncIOMotorDatabase


from app.domain.repositories.inbox_message_repository_interface import IInboxRepository
from app.domain.entities.inbox_message import InboxMessage


class MongoInboxRepository(IInboxRepository):

    COLLECTION = "inbox_messages"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[self.COLLECTION]


    async def exists_async(
        self, 
        event_id: str,
        session = None
    ) -> bool:
        
        message = await self._collection.find_one(
            {"event_id": event_id},
            session = session
        )

        return message is not None


    async def add_async(
        self, 
        message: InboxMessage,
        session = None 
    ) -> None:
        
        doc = message.model_dump(mode = "json")

        doc["_id"] = doc.pop("id")
        
        await self._collection.insert_one(
            doc,
            session = session
        )