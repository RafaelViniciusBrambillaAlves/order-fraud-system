import uuid
from app.domain.entities.order import Order
from app.application.use_cases.analyze_order import analyze_order
import logging
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.messaging.publishers.order_analyzed_publisher_interface import IOrderAnalyzedPublisher
from app.schemas.order_analyzed_event import OrderAnalyzedEvent

logger = logging.getLogger(__name__)

async def handle_order_created(
        event, 
        repository: IOrderRepository,
        publisher: IOrderAnalyzedPublisher
    ):

    fraud_status = analyze_order(event)

    analysis = Order(
        id = uuid.uuid4(),
        order_id = event.order_id,
        amount = event.amount,
        description = event.description,
        fraud_status = fraud_status
    )

    await repository.add(analysis)

    logger.info(
        "AUDIT | order_id=%s | fraud_status=%s | amount=%s",
        event.order_id,
        fraud_status,
        event.amount
    )

    outbound_event = OrderAnalyzedEvent(
        order_id = event.order_id,
        fraud_status = fraud_status
    )

    await publisher.publish(outbound_event)
    