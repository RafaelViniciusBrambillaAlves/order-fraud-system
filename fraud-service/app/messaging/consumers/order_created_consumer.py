import json 
import pika
import time
import logging

from app.schemas.order_created_event import OrderCreatedEvent
from app.application.handlers.order_created_handler import handle_order_created

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

def callback(ch, method, properties, body):
    try:
        logger.info(f"[x] Received Message: {method.routing_key}")
        data = json.loads(body)
        event = OrderCreatedEvent(**data)

        handle_order_created(event)

        ch.basic_ack(delivery_tag = method.delivery_tag)
        logger.info(f"[x] Message Processed: {method.routing_key}")

    except Exception as e:
        logger.error(f"[!] Error processing message: {e}")

        ch.basic_nack(delivery_tag = method.delivery_tag, requeue = False)


def start_consumer():
    while True: 
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host = 'rabbitmq',
                    heartbeat = 60,
                    blocked_connection_timeout = 300
                )
            )
            break

        except pika.exceptions.AMQPConnectionError:
            logger.warning("[!] RabbitMQ not available, retrying in 5 seconds...")
            time.sleep(5)
    
    channel = connection.channel()

    queue_args = {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "fraud.analysis.dlq",
        "x-message-ttl": 30000
    }

    # Exchange
    channel.exchange_declare(
        exchange = "order.events", 
        exchange_type = "direct", 
        durable = True
    )

    # Queue
    channel.queue_declare(
        queue = "fraud.analysis.queue", 
        durable = True,
        arguments = queue_args
    )

    channel.queue_bind(
        exchange = "order.events",
        queue = "fraud.analysis.queue",
        routing_key = "order.created" 
    )

    channel.basic_qos(prefetch_count = 1)

    channel.basic_consume(
        queue = "fraud.analysis.queue",
        on_message_callback = callback,
        auto_ack = False
    )

    print("[*] Waiting for order created events...")
    channel.start_consuming()
