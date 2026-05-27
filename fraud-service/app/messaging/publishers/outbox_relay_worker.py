"""
Worker assíncrono que publica mensagens PENDING do outbox no RabbitMQ.
 
Ciclo:
  1. Busca até 50 mensagens PENDING ordenadas por created_at
  2. Para cada mensagem: publica com confirm, marca SENT ou FAILED
  3. Persiste o status atualizado no MongoDB
  4. Dorme _POLLING_INTERVAL segundos e repete
 
Observabilidade:
  - Span de ciclo (outbox.relay.cycle) com batch size e resultado
  - Span de publicação individual (outbox.relay.publish) com routing_key
  - Histograma de duração do ciclo com tag de resultado
  - Histograma de duração individual de publicação
  - Contadores published/failed
"""

import asyncio 
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import aio_pika
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository
from app.observability.telemetry import tracer
from app.observability.amqp_propagation import inject_trace_context
from app.observability import fraud_metrics
from opentelemetry.trace import SpanKind
from app.domain.enums.outbox_status import OutboxStatus


logger = logging.getLogger(__name__)

_POLLING_INTERVAL = 1 # segundos entre cada ciclo

class OutboxRelayWorker:
    """
    Lê mensagens PENDING do outbox, publica no RabbitMQ e atualiza status.
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
            "OutboxRelayWorker started | polling_interval=%ds.", 
            _POLLING_INTERVAL
        )

        while True:

            try: 
                await self._process_batch()
            
            except asyncio.CancelledError:
                logger.info("OutboxRelayWorker cancelled")
                raise 

            except aio_pika.exceptions.AMQPConnectionError as exc:
                logger.warning(
                    "OutboxRelay: RabbitMQ unavailable (%s). "
                    "Messages stay PENDING in outbox. Retrying in %ds.",
                    exc, _POLLING_INTERVAL,
                )

            except Exception as exc:
                logger.error(
                    "OutboxRelayWorker cycle error | error=%s", 
                    exc, 
                    exc_info = True
                )
            
            await asyncio.sleep(_POLLING_INTERVAL)


    async def _process_batch(self) -> None:
   
        messages = await self._repository.get_pending_async(limit = 50)

        if not messages:
            return 
        
        with tracer.start_as_current_span(
            "outbox.relay.cycle",
            kind = SpanKind.INTERNAL
        ) as cycle_span:

            pending_count = len(messages)
            event_types = list({msg.event_type for msg in messages})

            cycle_span.set_attribute("outbox.batch.size", pending_count)
            cycle_span.set_attribute("outbox.pending_count", pending_count)
            cycle_span.set_attribute("outbox.event_types", ",".join(event_types))

            start = time.perf_counter()
            published = 0
            failed = 0
        
            async with await self._connection.channel() as channel:

                for msg in messages:
                    
                    await self._publish_message(channel, msg)

                    if msg.status == OutboxStatus.SENT:
                        published += 1

                    else:
                        failed += 1
                
            elapsed = time.perf_counter() - start

            cycle_span.set_attribute("outbox.batch.published", published)
            cycle_span.set_attribute("outbox.batch.failed", failed)
            cycle_span.set_attribute("outbox.cycle.duration_ms", round(elapsed * 1000, 2))

            cycle_result = (
                "all_failed" if failed == pending_count and pending_count > 0
                else "partial_failure" if failed > 0
                else "success"
            )

            if failed == pending_count and pending_count > 0:
                cycle_span.set_status(
                    Status(StatusCode.ERROR, "All messages failed to publish")
                )
            
            else:
                cycle_span.set_status(Status(StatusCode.OK))
            

            fraud_metrics.outbox_relay_duration.record(
                elapsed,
                {   
                    "result": cycle_result,
                    "published": published, 
                    "failed": failed
                }
            )

            logger.info(
                "OutboxRelay cycle | published=%d failed=%d result=%s duration=%.3fs",
                published,
                failed,
                cycle_result,
                elapsed * 1000,
            )


    async def _publish_message(self, channel, msg) -> None:
        """
        Publica uma única mensagem e atualiza seu status no repositório
        """

        with tracer.start_as_current_span(
            f"outbox.relay.publish {msg.exchange}/{msg.routing_key}",
            kind = SpanKind.PRODUCER
        ) as msg_span:
            
            msg_span.set_attribute("messaging.system", "rabbitmq")
            msg_span.set_attribute("messaging.destination", msg.exchange)
            msg_span.set_attribute("messaging.destination_kind", "exchange")
            msg_span.set_attribute("messaging.rabbitmq.routing_key", msg.routing_key)
            msg_span.set_attribute("messaging.operation", "publish")
            msg_span.set_attribute("outbox.message_id", str(msg.id))

            msg_span.set_attribute("outbox.event_type", msg.event_type)

            publish_start = time.perf_counter()

            try:
                exchange = await channel.get_exchange(msg.exchange)

                headers: dict = {}
                inject_trace_context(headers)

                amqp_message = aio_pika.Message(
                    body = msg.payload.encode(),
                    content_type = "application/json",
                    delivery_mode = aio_pika.DeliveryMode.PERSISTENT,
                    message_id = str(msg.id),
                    type = msg.event_type,
                    headers = headers
                )

                await exchange.publish(
                    amqp_message, 
                    routing_key = msg.routing_key
                )

                publish_elapsed = time.perf_counter() - publish_start

                fraud_metrics.publisher_duration.record(
                    publish_elapsed,
                    {
                        "exchange": msg.exchange,
                        "routing_key": msg.routing_key,
                        "result": "success"
                    }
                )

                msg.mark_as_sent()
                msg_span.set_status(Status(StatusCode.OK))

                fraud_metrics.outbox_messages_published_total.add(1, {
                    "routing_key": msg.routing_key
                })

                logger.info(
                    "Outbox sent | id=%s event=%s routing_key=%s duration_ms=%.1f",
                    msg.id, 
                    msg.event_type, 
                    msg.routing_key,
                    publish_elapsed * 1000
                )

            except Exception as exc:

                publish_elapsed = time.perf_counter() - publish_start
                
                msg_span.record_exception(exc)
                msg_span.set_status(Status(StatusCode.ERROR, str(exc)))

                fraud_metrics.publisher_duration.record(
                    publish_elapsed,
                    {
                        "exchange": msg.exchange,
                        "routing_key": msg.routing_key,
                        "result": "error"
                    }
                )

                fraud_metrics.processing_errors_total.add(
                    1, {"stage": "outbox_relay_publish"
                })
                fraud_metrics.outbox_messages_failed_total.add(
                    1, {"routing_key": msg.routing_key}
                )

                logger.error(
                    "Outbox publish failed | id=%s event=%s attempt=%d", 
                    "duration=%.1f error=%s",
                    msg.id, msg.event_type, msg.retry_count + 1,
                    publish_elapsed * 1000, exc,
                    exc_info = True
                )

                msg.mark_as_failed(str(exc))

            finally:
                await self._repository.save_async(msg)
                

