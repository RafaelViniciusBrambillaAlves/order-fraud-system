import uuid
from app.domain.entities.order import Order
from app.application.use_cases.analyze_order import analyze_order
import logging
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.schemas.order_analyzed_event import OrderAnalyzedEvent
from app.schemas.order_created_event import OrderCreatedEvent
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository

logger = logging.getLogger(__name__)

_EXCHANGE = "fraud.events"

async def handle_order_created(
        event: OrderCreatedEvent, 
        order_repository: IOrderRepository,
        outbox_repository: IOutboxMessageRepository,
        session
    ) -> None:

    fraud_status = analyze_order(event)

    order = Order(
        id = uuid.uuid4(),
        order_id = event.order_id,
        amount = event.amount,
        fraud_status = fraud_status
    )

    outbound = OrderAnalyzedEvent(
        order_id = event.order_id,
        fraud_status = fraud_status
    )

    routing_key = f"order.{fraud_status.lower()}"

    outbox_message = OutboxMessage.create(
        event_type = OrderAnalyzedEvent.__name__,
        payload = outbound.model_dump_json(),
        exchange = _EXCHANGE,
        routing_key = routing_key
    )

    await order_repository.add_async(order, session = session)
    await outbox_repository.add_async(outbox_message, session = session)

    logger.info(
        "AUDIT | order_id=%s | fraud_status=%s | amount=%s",
        event.order_id,
        fraud_status,
        event.amount,
    )
    