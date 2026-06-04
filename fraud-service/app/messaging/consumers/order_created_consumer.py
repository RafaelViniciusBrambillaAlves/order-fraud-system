"""
Consumer de mensagens order.created vindas do order-service.
 
Implementa o Inbox Pattern para idempotência:
  1. Abre sessão MongoDB com transação
  2. Verifica se o EventId já foi processado
  3. Executa análise antifraude e persiste resultado
  4. Registra InboxMessage na mesma transação
  5. Commit atômico — se qualquer passo falhar, nada é persistido
"""

import aio_pika
import logging
import time
from opentelemetry import trace

from motor.motor_asyncio import AsyncIOMotorClient
from app.schemas.order_created_event import OrderCreatedEvent
from app.application.handlers.order_created_handler import handle_order_created
from app.core.settings import settings
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository
from app.domain.repositories.inbox_message_repository_interface import IInboxRepository
from app.domain.entities.inbox_message import InboxMessage
from app.application.handlers.order_created_handler import handle_order_created
from app.schemas.order_created_event import OrderCreatedEvent
from app.observability.telemetry import tracer
from app.observability.amqp_propagation import extract_trace_context
from app.observability import fraud_metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace import SpanKind

logger = logging.getLogger(__name__)    

class OrderCreatedConsumer:

    QUEUE = "order.created.queue"
    EXCHANGE = "order.events"

    def __init__(
        self, 
        connection: aio_pika.abc.AbstractRobustConnection,
        mongo_client: AsyncIOMotorClient,
        order_repository = IOrderRepository,
        outbox_repository = IOutboxMessageRepository,
        inbox_repository = IInboxRepository
    ) -> None:
        self._connection = connection
        self._mongo_client = mongo_client
        self._order_repository = order_repository
        self._outbox_repository = outbox_repository
        self._inbox_repository = inbox_repository

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
            durable = True,
            arguments  = {
                "x-dead-letter-exchange": "dead.letter.exchange",
                "x-dead-letter-routing-key": "fraud.analysis.dlq"
            }
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
        """
        Handler de cada mensagem recebida.
 
        O span CONSUMER é aberto antes do process() para que exceções
        no parsing ou na transação ainda sejam capturadas no trace.
        """
        
        parent_context = extract_trace_context(message.headers)

        with tracer.start_as_current_span(
            name = "rabbitmq.consume order.created",
            context = parent_context,
            kind = SpanKind.CONSUMER
        ) as span:

            span.set_attribute("messaging.system", "rabbitmq")
            span.set_attribute("messaging.destination", self.QUEUE)
            span.set_attribute("messaging.destination_kind", "exchange")
            span.set_attribute("messaging.operation", "receive")
            span.set_attribute("messaging.rabbitmq.routing_key", "order.created")   
            span.set_attribute("messaging.message.body.size", len(message.body))

            fraud_metrics.messages_received_total.add(1)  
            start = time.perf_counter()

            # process(requeue=False) garante que exceções não tratadas mandam
            # a mensagem para a DLQ em vez de requeuear infinitamente
            async with message.process(requeue = False):

                try:
                    event = OrderCreatedEvent.model_validate_json(message.body)

                    span.set_attribute("order.id", str(event.order_id))
                    span.set_attribute("order.amount", float(event.amount))
                    span.set_attribute("event.id", event.event_id)

                    async with await self._mongo_client.start_session() as session:

                        async with session.start_transaction():
                            
                            # Idempotência 
                            already_processed = (
                                await self._inbox_repository.exists_async(
                                    event.event_id,
                                    session = session
                                )
                            )

                        if already_processed:

                            fraud_metrics.duplicate_messages_total.add(1)
                            span.set_attribute("message.duplicate", True)
                            span.set_status(Status(StatusCode.OK))

                            logger.warning(
                                "Message already processed | event_id=%s order_id=%s",
                                event.event_id, event.order_id
                            )

                            return 
                        
                        # Processamento principal
                        await handle_order_created(
                            event = event,
                            order_repository = self._order_repository,
                            outbox_repository = self._outbox_repository,
                            session = session 
                        )

                        inbox_message = InboxMessage.create(
                            event_id = event.event_id   
                        )

                        await self._inbox_repository.add_async(
                            inbox_message,
                            session = session
                        )
                    
                    duration = time.perf_counter() - start

                    span.set_attribute("message.duplicate", False)
                    span.set_attribute("consumer.duration_ms", round(duration * 1000, 2))
                    span.set_status(Status(StatusCode.OK))

                    fraud_metrics.message_processing_duration.record(
                        duration,
                        {"result": "success"}
                    )

                    logger.info(
                        "Message processed | event_id=%s order_id=%s "
                        "amount=%s duration_ms=%.1f",
                        event.event_id, event.order_id,
                        event.amount, duration * 1000,
                    )
                
                except Exception as exc:
                    duration = time.perf_counter() - start

                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))

                    fraud_metrics.processing_errors_total.add(
                        1, {"stage": "consumer"}
                    )

                    fraud_metrics.message_processing_duration.record(
                        duration, {"result": "error"}
                    )

                    logger.error(
                        "Error processing menssage | event_id=%s "
                        "duration_ms=%.1f error=%s",
                        getattr(event, "event_id", "unknown"),
                        duration * 1000,
                        exc,
                        exc_info=True,
                    )

                    raise
            