import aio_pika
import logging
import json
from app.core.settings import settings
from app.messaging.publishers.order_analyzed_publisher_interface import IOrderAnalyzedPublisher
from app.schemas.order_analyzed_event import OrderAnalyzedEvent
from typing import Optional

logger = logging.getLogger(__name__)

class OrderAnalyzedPublisher(IOrderAnalyzedPublisher):

    EXCHANGE_NAME = "fraud.events"
    ROUTING_NAME = "order.analyzed"

    def __init__(self) -> None:
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(settings.rabbit_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )

        logger.info(
            "RabbitMQOrderAnalyzedPublisher | Connected | Exchange: %s",
            self.EXCHANGE_NAME,
        )

    async def close(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQOrderAnalyzedPublisher | Connection closed")

    async def publish(self, event: OrderAnalyzedEvent) -> None:
        if self._exchange is None:
            raise RuntimeError(
                "Publisher não inicializado. Chame connect() antes de publish()."
            )
        
        payload = event.model_dump_json()

        message = aio_pika.Message(
            body = payload.encode(),
            content_type = "application/json",
            delivery_mode = aio_pika.DeliveryMode.PERSISTENT
        )

        # await self._exchange.publish(message, routing_key = self.ROUTING_NAME)
        await self._exchange.publish(message, routing_key = f"order.{event.fraud_status.lower()}")

        logger.info(
            "PUBLISH | order_id=%s | fraud_status=%s",
            event.order_id,
            event.fraud_status,
        )