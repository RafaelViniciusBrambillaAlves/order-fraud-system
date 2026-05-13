import aio_pika
import logging
from datetime import datetime, timezone
from typing import Any 

from app.messaging.models.dlq_message import DlqMessage

logger = logging.getLogger(__name__)

class DlqConsumer:

    def __init__(
        self,
        connection: aio_pika.abc.AbstractRobustConnection,
        queue_name: str
    ):
        self._connection = connection
        self._queue_name = queue_name

    async def start(self) -> None:

        channel = await self._connection.channel()

        await channel.set_qos(prefetch_count = 1)

        queue = await channel.declare_queue(
            self._queue_name,
            durable = True,
            arguments = {
                "x-message-ttl": 604800000,
                "x-queue-type": "classic"
            }
        ) 

        await queue.consume(self._on_message)

        logger.info(
            "DLQ Consumer listening | queue=%s",
            self._queue_name
        )

    async def _on_message(
        self,
        message: aio_pika.IncomingMessage
    ) -> None:
            
        async with message.process(requeue = False):
              
            try:
                dlq_message = self._extract_dlq_message(message)

                logger.error(
                    "Dead letter message received | "
                    "queue=%s "
                    "message_id=%s "
                    "event_type=%s "
                    "source_queue=%s "
                    "routing_key=%s "
                    "death_reason=%s "
                    "death_count=%s "
                    "first_death_at=%s "
                    "body=%s",
                    self._queue_name,
                    dlq_message.message_id,
                    dlq_message.event_type,
                    dlq_message.source_queue,
                    dlq_message.routing_key,
                    dlq_message.death_reason,
                    dlq_message.death_count,
                    dlq_message.first_death_at,
                    dlq_message.body[:500]
                )

                await self.on_dead_letter_received(dlq_message)
                
            except Exception as exc:

                logger.error(
                    "DLQ processing failed | queue=%s error=%s",
                    self._queue_name,
                    exc,
                    exc_info = True
                )

    def _extract_dlq_message(
        self,
        message: aio_pika.IncomingMessage,
    ) -> DlqMessage:
        
        headers = message.headers or {}

        source_queue = "unknown"
        death_reason = "unknown"
        death_count = 0
        first_death_at = datetime.now(timezone.utc)

        x_death = headers.get("x-death")

        if isinstance(x_death, list) and len(x_death) > 0:

            death_info: dict[str, Any] = x_death[0]

            source_queue = death_info.get("queue", "unknown")
            death_reason = death_info.get("reason", "unknown")
            death_count = death_info.get("count", 0)

            death_time = death_info.get("time")

            if death_time:
                first_death_at = death_time

        return DlqMessage(
            message_id = message.message_id or "unknown",
            event_type = message.type or "unknown",
            source_queue = source_queue,
            routing_key = message.routing_key,
            death_reason = death_reason,
            death_count = death_count,
            first_death_at = first_death_at,
            body = message.body.decode(errors = "ignore") 
        )
    
    async def on_dead_letter_received(
        self,
        message: DlqMessage
    ) -> None:
        """
        Hook para futuras integrações:
        """
        return 