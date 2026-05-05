from fastapi import Depends, FastAPI, Request
from contextlib import asynccontextmanager
import threading
import asyncio
from app.infrastructure.database.client import MongoDatabase
import logging
from app.infrastructure.database.repositories.mongo_order_repository import MongoOrderRepository
from app.messaging.consumers.order_created_consumer import start_consumer
from fastapi import HTTPException
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.messaging.publishers.order_analyzed_publisher import OrderAnalyzedPublisher

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configura Dependências

    # Banco de Dados
    mongo = MongoDatabase()
    db = mongo.get_database()
    repository = MongoOrderRepository(db)

    # Publisher RabbitMQ
    publisher = OrderAnalyzedPublisher()
    await publisher.connect()

    # Estado global
    app.state.repository = repository
    app.state.publisher = publisher
    app.state.mongo = mongo

    # Consumer em thread separado
    loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target = start_consumer, 
        args = (loop, repository, publisher),
        daemon = True 
    )
    thread.start()

    logger.info("Fraud Service | Started")

    yield 

    # Shutdown
    await publisher.close()
    await mongo.close()
    logger.info("Fraud Service | Shutdown complete")


app = FastAPI(
        title = "Fraud Service",
        lifespan = lifespan
    )


def get_repository(request: Request) -> IOrderRepository:
    return request.app.state.repository

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
