from fastapi import Depends, FastAPI, Request
from contextlib import asynccontextmanager
import asyncio
from app.infrastructure.database.client import MongoDatabase
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from app.infrastructure.database.repositories.mongo_order_repository import MongoOrderRepository
from fastapi import HTTPException
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.messaging.publishers.order_analyzed_publisher import OrderAnalyzedPublisher
from app.core.settings import settings
import aio_pika
from app.messaging.consumers.order_created_consumer import OrderCreatedConsumer
from app.messaging.publishers.outbox_relay_worker import OutboxRelayWorker
from app.infrastructure.database.repositories.mongo_outbox_repository import MongoOutboxRepository

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configura Dependências

    # Banco de Dados
    mongo_client  = AsyncIOMotorClient(settings.mongodb_url)
    db = mongo_client[settings.mongodb_database]

    await MongoDatabase.ensure_indexes(db)
    
    rabbit_conn = await aio_pika.connect_robust(settings.rabbitmq_url)
    
    order_repository = MongoOrderRepository(db)
    outbox_repository = MongoOutboxRepository(db)

    app.state.order_repository = order_repository   

    consumer = OrderCreatedConsumer(
        connection = rabbit_conn,
        mongo_client = mongo_client,
        order_repository = order_repository,
        outbox_repository = outbox_repository
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
    logger.info("Fraud service stopped.")


app = FastAPI(
        title = "Fraud Service",
        lifespan = lifespan
    )


def get_repository(request: Request) -> IOrderRepository:
    return request.app.state.order_repository

# Endpoints

@app.get("/health", tags = ["Infra"])
def home():
    return {"status": "ok", "service": "fraud-service"}


@app.get("/orders/{order_id}", tags = ["Orders"])
async def get_order_analysis(
    order_id: str, 
    repository: MongoOrderRepository = Depends(get_repository)
): 
    order = await repository.get_by_id(order_id)

    if not order:
      raise HTTPException(status_code = 404, detail = "Order not found")
    
    return order
    

@app.get("/orders", tags = ["Orders"])
async def list_orders(
    repository: MongoOrderRepository = Depends(get_repository)
):
    return await repository.list_all()
