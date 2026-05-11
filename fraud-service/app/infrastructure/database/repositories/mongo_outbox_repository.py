from typing import List, Any
from uuid import UUID
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.enums.outbox_status import OutboxStatus

class MongoOutboxRepository(IOutboxMessageRepository):

    COLLECTION = "outbox_messages"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[self.COLLECTION]


    async def add_async(
        self, 
        message: OutboxMessage, 
        session: Any | None = None
    ) -> None:
        await self._collection.insert_one(
            self._to_document(message), 
            session = session
        )


    async def get_pending_async(
        self, 
        limit: int = 50
    ) -> List[OutboxMessage]:
        cursor = (
            self._collection
            .find({
                "status": int(OutboxStatus.PENDING)
            })
            .sort("created_at", 1)
            .limit(limit)
        )
        docs = await cursor.to_list(length = limit)

        return [self._from_document(d) for d in docs]        


    async def save_async(
        self, 
        message: OutboxMessage
    ) -> None:
        sent_at = (
            message.sent_at.replace(tzinfo = timezone.utc)
            if message.sent_at and message.sent_at.tzinfo is None
            else message.sent_at
        )
        
        await self._collection.update_one(
            {"_id": str(message.id)},
            {
                "$set":{
                "status": int(message.status),
                "sent_at": sent_at,
                "retry_count": message.retry_count,
                "last_error": message.last_error
                }
            }
        )


    # helpers
    @staticmethod
    def _to_document(message: OutboxMessage) -> dict:
        return {
            "_id": str(message.id),
            "event_type": message.event_type,
            "payload": message.payload,
            "exchange": message.exchange,
            "routing_key": message.routing_key,
            "status": int(message.status),
            "created_at": message.created_at,
            "sent_at": message.sent_at,
            "retry_count": message.retry_count,
            "last_error": message.last_error
        }
    
    @staticmethod
    def _from_document(doc: dict) -> OutboxMessage:
        return OutboxMessage(
            id = UUID(doc["_id"]),
            event_type = doc["event_type"],
            payload = doc["payload"],
            exchange = doc["exchange"],
            routing_key = doc["routing_key"],
            status = OutboxStatus(doc["status"]),
            created_at = doc["created_at"],
            sent_at = doc.get("sent_at"),
            retry_count = doc.get("retry_count", 0),
            last_error = doc.get("last_error"),
        )
    