import asyncio 
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import aio_pika
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository


logger = logging.getLogger(__name__)

_POLLING_INTERVAL = 1 # segundos entre cada ciclo

class OutboxRelayWorker:
    """
    Worker Assincrono:
        Le mensagem Peding da outbox_messages
        Publica no RabbitMq com confirmação
        Marca como SENT ou incrementa FAILED
    """

    def __init__(
        self,
        outbox_repository: IOutboxMessageRepository,
        connection: aio_pika.abc.AbstractRobustConnection
    ) -> None:
        self._repository = outbox_repository
        self._connection = connection

    
    async def run(self) -> None:

        logger.info(
            "OutboxRelayWorker started. Polling every %ds.", 
            _POLLING_INTERVAL
        )

        while True:

            try: 
                await self._process_batch()
            
            except asyncio.CancelledError:
                logger.info("OutboxRelayWorker cancelled.")
                raise 

            except aio_pika.exceptions.AMQPConnectionError as exc:
                logger.warning(
                    "OutboxRelay: RabbitMQ unavailable (%s). "
                    "Messages stay PENDING in outbox. Retrying in %ds.",
                    exc, _POLLING_INTERVAL,
                )

            except Exception as exc:
                logger.error(
                    "OutboxRelayWorker cycle error: %s", 
                    exc, 
                    exc_info = True
                )
            
            await asyncio.sleep(_POLLING_INTERVAL)


    async def _process_batch(self) -> None:
   
        messages = await self._repository.get_pending_async(limit = 50)

        if not messages:
            return 
        
        logger.info(
            "OutboxRelay: processing %d pending message(s).", 
            len(messages)
        )

        async with await self._connection.channel() as channel:
            for msg in messages:
                try:
                    exchange = await channel.get_exchange(msg.exchange,)

                    amqp_message = aio_pika.Message(
                        body = msg.payload.encode(),
                        content_type = "application/json",
                        delivery_mode = aio_pika.DeliveryMode.PERSISTENT,
                        message_id = str(msg.id),
                        type = msg.event_type
                    )

                    await exchange.publish(
                        amqp_message, 
                        routing_key = msg.routing_key
                    )

                    msg.mark_as_sent()

                    logger.info(
                        "Outbox sent | id=%s event=%s routing_key=%s",
                        msg.id, msg.event_type, msg.routing_key,
                    )

                except Exception as exc:
                    logger.error(
                        "Outbox publish failed | id=%s attempt=%d error=%s",
                        msg.id, msg.retry_count + 1, exc,
                    )
                    msg.mark_as_failed(str(exc))

                finally:
                    await self._repository.save_async(msg)




