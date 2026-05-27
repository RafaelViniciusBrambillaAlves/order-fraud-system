"""
Handler de negócio para o evento OrderCreated.
 
Orquestra:
  1. Análise antifraude (regras de negócio, sem I/O)
  2. Construção das entidades de resultado
  3. Persistência atômica no MongoDB (dentro da sessão/transação passada pelo caller)
"""

import uuid
import time
import logging
from opentelemetry.trace import Status, StatusCode

from app.domain.entities.order import Order
from app.application.use_cases.analyze_order import analyze_order
import logging
from app.domain.repositories.order_repository_interface import IOrderRepository
from app.schemas.order_analyzed_event import OrderAnalyzedEvent
from app.schemas.order_created_event import OrderCreatedEvent
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.repositories.outbox_message_repository_interface import IOutboxMessageRepository
from app.observability.telemetry import tracer
from app.observability import fraud_metrics
from opentelemetry.trace import SpanKind

logger = logging.getLogger(__name__)

_EXCHANGE = "fraud.events"

# Limiar que define rejeição, deve bater com a regra em analyze_order
# Exposto como atributo no span para facilitar correlação no Jaeger
_FRAUD_THRESHOLD = 1000.0



async def handle_order_created(
    event: OrderCreatedEvent, 
    order_repository: IOrderRepository,
    outbox_repository: IOutboxMessageRepository,
    session
) -> None:
    """
    Orquestra o fluxo completo de análise antifraude.
 
    Args:
        event:              Evento desserializado vindo do consumer.
        order_repository:   Repositório de pedidos (MongoDB).
        outbox_repository:  Repositório de outbox (MongoDB).
        session:            Sessão MongoDB com transação aberta pelo consumer.
    """
    with tracer.start_as_current_span(
        "fraud.handle_order_created",
        kind = SpanKind.INTERNAL
    ) as span:

        span.set_attribute("order.id", str(event.order_id))
        span.set_attribute("order.amount", float(event.amount))
        span.set_attribute("event.id", event.event_id)

        if hasattr(event, "customer_id") and event.customer_id:
            span.set_attribute("customer.id", str(event.customer_id))
        
        start = time.perf_counter()

        try: 
            fraud_status = _run_analysis(event, span)

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

            await _persist(order, outbox_message, order_repository, outbox_repository, session)

            duration = time.perf_counter() - start 

            span.set_attribute("handler.duration_ms", round(duration * 1000, 2))
            span.set_status(Status(StatusCode.OK))

            logger.info(
                "Order analyse | order_id=%s fraud_status=%s amount=%s",
                "routing_key=%s duration_ms=%.1f",
                event.order_id, fraud_status, event.amount,
                routing_key, duration * 1000
            )   
        
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            fraud_metrics.processing_errors_total.add(1, {"stage": "handler"})

            logger.error(
                "Handler order_created Failed | order_id=%s error=%s",
                event.order_id, exc
            )
            raise    

def _run_analysis(event: OrderCreatedEvent, parent_span) -> str:
    """
    Executa a análise antifraude e registra métricas e span filho.
    """
    with tracer.start_as_current_span(
        "fraud.analyze_order",
        kind = SpanKind.INTERNAL
    ) as analysis_span:

        start = time.perf_counter()
        fraud_status = analyze_order(event)
        elapsed = time.perf_counter() - start

        analysis_span.set_attribute("fraud.status", str(fraud_status))
        analysis_span.set_attribute("fraud.rule", "amount_threshold")
        analysis_span.set_attribute("fraud.threshold", _FRAUD_THRESHOLD)
        analysis_span.set_attribute("fraud.score", float(event.amount))
        analysis_span.set_status(Status(StatusCode.OK))

        parent_span.set_attribute("fraud.status", str(fraud_status))

        fraud_metrics.analysis_duration.record(elapsed)
        
        fraud_metrics.orders_analyzed_total.add(
            1, {"fraud_status": str(fraud_status).lower()}
        )

        fraud_metrics.fraud_decisions_total.add(1, {
            "decission": str(fraud_status).lower(),
            "rule": "amount_threshould"
        })

        return  fraud_status
    
async def _persist(
    order: Order, 
    outbox_message: OutboxMessage, 
    order_repository: IOrderRepository, 
    outbox_repository: IOutboxMessageRepository,
    session
) -> None:
    """
    Persiste order + outbox_message dentro da sessão/transação MongoDB passada.
    Ambos os documentos são inseridos atomicamente.
    """

    with tracer.start_as_current_span(
        "fraud.persist",
        kind = SpanKind.INTERNAL
    ) as db_span:
        
        db_span.set_attribute("db.system", "mongodb")
        db_span.set_attribute("db.operation", "insert")

        db_span.set_attribute("db.mongo.collection", "orders,outbox_messages")

        db_span.set_attribute("db.mongo.documents", 2)

        start = time.perf_counter()

        await order_repository.add_async(order, session = session)
        await outbox_repository.add_async(outbox_message, session = session)

        elapsed = time.perf_counter() - start

        fraud_metrics.mongodb_operation_duration.record(
            elapsed,
            {"operation": "transaction_insert"}
        )
                                                
        db_span.set_status(Status(StatusCode.OK))
