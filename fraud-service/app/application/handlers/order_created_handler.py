from app.schemas.order_created_event import OrderCreatedEvent
from app.application.use_cases.analyze_order import analyze_order
import logging

logger = logging.getLogger(__name__)

def handle_order_created(event: OrderCreatedEvent):

    result = analyze_order(event)

    logger.info(f"AUDIT | Order: {event.order_id} | Status: {result} | Amount: {event.amount}")

    return result