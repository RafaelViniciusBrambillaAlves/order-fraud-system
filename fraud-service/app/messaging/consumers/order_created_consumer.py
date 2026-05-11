import aio_pika
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.schemas.order_created_event import OrderCreatedEvent
from app.application.handlers.order_created_handler import handle_order_created
from app.core.settings import settings
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository
from app.application.handlers.order_created_handler import handle_order_created
from app.schemas.order_created_event import OrderCreatedEvent

logger = logging.getLogger(__name__)    

class OrderCreatedConsumer:

    QUEUE = "order.created.queue"
    EXCHANGE = "order.events"

    def __init__(
        self, 
        connection: aio_pika.abc.AbstractRobustConnection,
        mongo_client: AsyncIOMotorClient,
        order_repository = IOrderRepository,
        outbox_repository = IOutboxMessageRepository
    ) -> None:
        self._connection = connection
        self._mongo_client = mongo_client
        self._order_repository = order_repository
        self._outbox_repository = outbox_repository

    async def start(self) -> None:

        channel = await self._connection.channel()

        await channel.set_qos(prefetch_count = 1)

        exchange = await channel.declare_exchange(
            self.EXCHANGE, 
            aio_pika.ExchangeType.DIRECT,
            durable = True
        )

        queue = await channel.declare_queue(
            self.QUEUE, 
            durable = True
        )

        await queue.bind(
            exchange, 
            routing_key = "order.created"
        )

        await queue.consume(self._on_message)

        logger.info(
            "OrderCreatedConsumer | listening on '%s'", 
            self.QUEUE
        )

    async def _on_message(
        self, 
        message: aio_pika.IncomingMessage
    ) -> None:

        async with message.process(requeue = False):
            try:
                event = OrderCreatedEvent.model_validate_json(message.body)

                async with await self._mongo_client.start_session() as session:

                    async with session.start_transaction():

                        await handle_order_created(
                            event = event,
                            order_repository = self._order_repository,
                            outbox_repository = self._outbox_repository,
                            session = session
                        )

            except Exception as exc:
                logger.error(
                    "Error processing message: %s",
                    exc,
                    exc_info = True
                )
                return 

            