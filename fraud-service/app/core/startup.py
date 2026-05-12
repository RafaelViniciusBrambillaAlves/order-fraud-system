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
import asyncio

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):

    mongo_client = AsyncIOMotorClient(settings.mongodb_url)

    db = mongo_client[settings.mongodb_database]

    await MongoDatabase.ensure_indexes(db)

    rabbit_conn = await aio_pika.connect_robust(settings.rabbitmq_url)

    order_repository = MongoOrderRepository(db)
    outbox_repository = MongoOutboxRepository(db)
    inbox_respository = MongoInboxRepository(db)

    app.state.order_repository = order_repository

    consumer = OrderCreatedConsumer(
        connection = rabbit_conn,
        mongo_client = mongo_client,
        order_repository = order_repository,
        outbox_repository = outbox_repository,
        inbox_repository = inbox_respository
    )

    await consumer.start()

    relay = OutboxRelayWorker(
        outbox_repository = outbox_repository,
        connection = rabbit_conn
    )

    relay_task = asyncio.create_task(
        relay.run(),
        name = "outbox-relay"
    )

    logger.info("Fraud service started.")

    yield

    relay_task.cancel()

    try:
        await relay_task
    
    except asyncio.CancelledError:
        pass

    await rabbit_conn.close()
    mongo_client.close()

    logger.info("Fraud service stopped")


