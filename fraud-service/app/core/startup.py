from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings
from app.infrastructure.database.client import MongoDatabase
import aio_pika
from app.infrastructure.database.repositories.mongo_order_repository import MongoOrderRepository
from app.infrastructure.database.repositories.mongo_outbox_repository import MongoOutboxRepository
from app.messaging.consumers.order_created_consumer import OrderCreatedConsumer
from app.messaging.publishers.outbox_relay_worker import OutboxRelayWorker
from app.infrastructure.database.repositories.mongo_inbox_repository import MongoInboxRepository
from app.messaging.consumers.dlq_consumer import DlqConsumer
import asyncio
from app.observability import fraud_metrics


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida completo do fraud-service.
    Startup → yield → shutdown.
    """
    logger.info("Fraud-service starting...")

    # MongoDB
    mongo_client = AsyncIOMotorClient(
        settings.mongodb_url,
        uuidRepresentation = "standard"
    )

    db = mongo_client[settings.mongodb_database]

    try:
        await MongoDatabase.ensure_indexes(db)
        logger.info("MongoDb connected | db=%s", settings.mongodb_database)
        fraud_metrics.mongodb_connection_status.add(1)
    
    except Exception:
        logger.exception("Failed to MongoDB connected")
        fraud_metrics.mongodb_connection_status.add(-1)
        raise

    # RabbitMQ
    try:
        rabbit_conn = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            heartbeat = settings.rabbitmq_heartbeat
        )

        logger.info("RabbitMQ Conncted | url=%s", settings.rabbitmq_url)
        fraud_metrics.rabbitmq_connection_status.add(1)

    except Exception:
        logger.exception("Faile to RabbitMQ connected")
        fraud_metrics.rabbitmq_connection_status.add(-1)
        mongo_client.close()
        raise


    # Repositorios
    order_repository = MongoOrderRepository(db)
    outbox_repository = MongoOutboxRepository(db)
    inbox_respository = MongoInboxRepository(db)
    # Disponibiliza o repositório de pedidos para as rotas HTTP via app.state.
    app.state.order_repository = order_repository

    # Gauge de outbox pendentes 
    # Registra o callback periodicamente para obter
    # a contagem real de mensagens PENDING no outbox
    try: 
        fraud_metrics.register_outbox_pending_callback(
            outbox_repository.count_peding_sync
        )
        logger.info("Gauge fraud.outbox.peding.current register")
    
    except Exception:
        logger.warning("Failed to register pending outbox gauges")


    # Consumer principal
    consumer = OrderCreatedConsumer(
        connection = rabbit_conn,
        mongo_client = mongo_client,
        order_repository = order_repository,
        outbox_repository = outbox_repository,
        inbox_repository = inbox_respository
    )
    await consumer.start()
    logger.info("OrderCreatedConsumer started")

    # Outbox relay worker
    relay = OutboxRelayWorker(
        outbox_repository = outbox_repository,
        connection = rabbit_conn
    )

    relay_task = asyncio.create_task(
        relay.run(),
        name = "outbox-relay"
    )
    logger.info("OutboxRelayWorker started")
    
    # DLQ consumer
    fraud_dlq_consumer = DlqConsumer(
        connection = rabbit_conn,
        queue_name = "fraud.analysis.dlq"
    )

    await fraud_dlq_consumer.start()
    logger.info("DlqConsumer started | queue=fraud.analysis.dlq")

    logger.info("Fraud service ready to receive messages")

    yield

    logger.info("Fraud-service closing...")

    relay_task.cancel()

    try:
        await relay_task 
    except asyncio.CancelledError:
        logger.info("OutboxRelayWorker closing")
    
    try:
        await rabbit_conn.close()
        fraud_metrics.rabbitmq_connection_status.add(-1)
        logger.info("RabbitMQ Connection closing")
    except Exception:
        logger.warning("Error closing RabbitMQ connection", exc_info = True)

    try:
        mongo_client.close()
        fraud_metrics.mongodb_connection_status.add(-1)
        logger.info("MongoDb connection closing")
    except Exception:
        logger.warning("Error closing MongoDB connection", exc_info = True)

    logger.info("Fraud service stopped")