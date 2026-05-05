import json
import traceback 
import pika
import time
import logging
import asyncio
from app.schemas.order_created_event import OrderCreatedEvent
from app.application.handlers.order_created_handler import handle_order_created
from app.core.settings import settings
from functools import partial
from app.messaging.publishers.order_analyzed_publisher_interface import IOrderAnalyzedPublisher
from app.domain.repositories.order_repository_interface import IOrderRepository

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)    

EXCHANGE = "order.events"
QUEUE = "fraud.analysis.queue"
ROUTING_KEY = "order.created"
DLQ_ROUTING_KEY = "fraud.analysis.dlq"

def _callback(
        ch, 
        method, 
        properties, 
        body, 
        loop, 
        repository, 
        publisher: IOrderAnalyzedPublisher
) -> None:
    
    try:
        logger.info(
            "OrderCreatedConsumer | Received | routing_key=%s",
            method.routing_key
        )

        event = OrderCreatedEvent(**json.loads(body))

        future = asyncio.run_coroutine_threadsafe(
           handle_order_created(event, repository, publisher), 
           loop
        )
    
        future.result()

        ch.basic_ack(delivery_tag = method.delivery_tag)
        logger.info(
            "OrderCreatedConsumer | Processed | order_id=%s",
            event.order_id,
        )

    except Exception as e:
        logger.error(
            "OrderCreatedConsumer | Failed | routing_key=%s | error=%s",
            method.routing_key,
            e,
        )
        logger.error(traceback.format_exc())

        ch.basic_nack(delivery_tag = method.delivery_tag, requeue = False)


def _setup_channel(
    connection: pika.BlockingConnection, 
    loop: asyncio.AbstractEventLoop, 
    repository: IOrderRepository,
    publisher: IOrderAnalyzedPublisher
) -> pika.adapters.blocking_connection.BlockingChannel:
    
    channel = connection.channel()

    # Exchange
    channel.exchange_declare(
        exchange = EXCHANGE, 
        exchange_type = "direct", 
        durable = True
    )

    # Queue
    channel.queue_declare(
        queue = QUEUE, 
        durable = True,
        arguments = {
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ_ROUTING_KEY    ,
            "x-message-ttl": 30000
        }
    )

    channel.queue_bind(
        exchange = EXCHANGE,
        queue = QUEUE,
        routing_key = ROUTING_KEY 
    )

    channel.basic_qos(prefetch_count = 1)

    channel.basic_consume(
        queue = QUEUE,
        on_message_callback = partial(
            _callback, 
            loop = loop, 
            repository = repository,
            publisher = publisher
        ),
        auto_ack = False
    )

    return channel

def start_consumer(
    loop: asyncio.AbstractEventLoop, 
    repository: IOrderRepository, 
    publisher: IOrderAnalyzedPublisher
) -> None:
    while True: 
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host = settings.rabbitmq_host,
                    heartbeat = settings.rabbit_heartbeat,
                    blocked_connection_timeout = 300
                )
            )

            channel = _setup_channel(connection, loop, repository, publisher)
            
            logger.info("OrderCreatedConsumer | Waiting for events | queue=%s", QUEUE)

            channel.start_consuming()

        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.ConnectionClosedByBroker,
            pika.exceptions.ChannelClosedByBroker
        ) as e:
            logger.warning(
                "OrderCreatedConsumer | Connection lost | reason=%s | retrying in 5s",
                e.__class__.__name__,
            )
            time.sleep(5)

        except Exception as e:
            logger.error(
                "OrderCreatedConsumer | Unexpected error | error=%s",
                e,
            )
            logger.error(traceback.format_exc())
            time.sleep(5)
    
    
