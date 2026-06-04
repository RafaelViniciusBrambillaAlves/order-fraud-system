"""
Fixtures compartilhadas para testes do fraud-service.

Define mocks, objetos de teste padrão e configurações para pytest-asyncio.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.domain.entities.order import Order
from app.domain.entities.inbox_message import InboxMessage
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.enums.fraud_status import FraudStatus
from app.domain.enums.outbox_status import OutboxStatus
from app.schemas.order_created_event import OrderCreatedEvent


# ============================================================================
# Configuração do pytest-asyncio
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Fornece o event loop para testes assíncronos."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Eventos de Teste
# ============================================================================

@pytest.fixture
def sample_order_created_event(order_id: UUID, event_id: str) -> OrderCreatedEvent:
    """Evento OrderCreated padrão para testes (amount=500 → APPROVED)."""
    return OrderCreatedEvent(
        event_id=event_id,
        order_id=order_id,
        amount=500.0,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_order_created_event_high_amount(order_id: UUID, event_id: str) -> OrderCreatedEvent:
    """Evento OrderCreated com valor acima do threshold (1500 > 1000 → REJECTED)."""
    return OrderCreatedEvent(
        event_id=event_id,
        order_id=order_id,
        amount=1500.0,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_order_created_event_at_threshold(order_id: UUID, event_id: str) -> OrderCreatedEvent:
    """Evento OrderCreated com valor exatamente no threshold (1000.0 → APPROVED, regra é > 1000)."""
    return OrderCreatedEvent(
        event_id=event_id,
        order_id=order_id,
        amount=1000.0,
        created_at=datetime.now(timezone.utc)
    )


# ============================================================================
# Entidades de Domínio
# ============================================================================

@pytest.fixture()
def order_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture()
def event_id() -> str:
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def sample_order(order_id: UUID):
    """Order padrão para testes."""
    return Order(
        order_id=order_id,
        amount=500.0,
        fraud_status=FraudStatus.APPROVED
    )


@pytest.fixture
def sample_outbox_message():
    """OutboxMessage padrão para testes."""
    return OutboxMessage.create(
        event_type="OrderAnalyzed",
        payload='{"orderId":"123","status":"APPROVED"}',
        exchange="fraud.events",
        routing_key="order.approved"
    )


@pytest.fixture
def sample_inbox_message(event_id: str):
    """InboxMessage padrão para testes."""
    return InboxMessage.create(event_id=event_id)


# ============================================================================
# Mocks de Repositórios
# ============================================================================

@pytest.fixture
def mock_order_repository() -> AsyncMock:
    """Mock de IOrderRepository com métodos assíncronos."""
    repo = AsyncMock()
    repo.add_async = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_outbox_repository() -> AsyncMock:
    """Mock de IOutboxMessageRepository com métodos assíncronos."""
    repo = AsyncMock()
    repo.add_async = AsyncMock(return_value=None)
    repo.get_pending_async = AsyncMock(return_value=[])
    repo.save_async = AsyncMock(return_value=None)
    repo.count_pending_async = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_inbox_repository() -> AsyncMock:
    """Mock de IInboxRepository com métodos assíncronos."""
    repo = AsyncMock()
    repo.exists_async = AsyncMock(return_value=False)
    repo.add_async = AsyncMock(return_value=None)
    return repo


# ============================================================================
# Mocks de MongoDB Session e Contexto
# ============================================================================

@pytest.fixture
def mock_session() -> MagicMock:
    """
    Mock de sessão MongoDB (motor AsyncIOMotorClientSession).

    O Motor expõe start_transaction() como um context manager SÍNCRONO
    (não async), apesar da sessão em si ser assíncrona:

        async with await client.start_session() as session:  # async
            with session.start_transaction():                # síncrono
                ...

    Por isso start_transaction usa MagicMock com __enter__/__exit__,
    não AsyncMock.
    """
    session = MagicMock()
    # start_transaction é síncrono no Motor — usa "with", não "async with"
    transaction_cm = MagicMock()
    transaction_cm.__enter__ = MagicMock(return_value=None)
    transaction_cm.__exit__ = MagicMock(return_value=False)
    session.start_transaction = MagicMock(return_value=transaction_cm)
    # Métodos assíncronos da sessão
    session.commit_transaction = AsyncMock()
    session.abort_transaction = AsyncMock()
    return session


@pytest.fixture
def mock_mongo_client(mock_session: MagicMock) -> AsyncMock:
    """
    Mock de AsyncIOMotorClient MongoDB.

    O consumer usa o padrão:
        async with await self._mongo_client.start_session() as session:

    Portanto start_session() precisa:
      1. ser awaitable  (retornar um coroutine ou ser AsyncMock)
      2. retornar um async context manager cujo __aenter__ devolve mock_session
    """
    client = AsyncMock()

    # Async context manager que entrega mock_session no "as session"
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    # start_session() é awaited antes do "async with", logo precisa ser AsyncMock
    # retornando o context manager
    client.start_session = AsyncMock(return_value=session_cm)

    return client


# ============================================================================
# Mocks de Logging e Observabilidade
# ============================================================================

@pytest.fixture
def mock_logger():
    """Mock de logger (logging.Logger)."""
    return MagicMock()


@pytest.fixture
def mock_tracer():
    """Mock de tracer OpenTelemetry (Tracer)."""
    tracer = MagicMock()
    tracer.start_as_current_span = MagicMock()
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.set_attribute = MagicMock()
    tracer.start_as_current_span.return_value = span
    return tracer


@pytest.fixture
def mock_metrics():
    """Mock de métricas OpenTelemetry."""
    metrics = MagicMock()
    metrics.add = MagicMock()
    metrics.record = MagicMock()
    return metrics


# ============================================================================
# Mocks de RabbitMQ / AMQP
# ============================================================================

@pytest.fixture
def mock_amqp_message():
    """
    Mock genérico de mensagem AMQP (aio_pika.IncomingMessage).
    Para testes E2E use as fixtures específicas (valid_amqp_message, etc.)
    ou a factory make_amqp_message.
    """
    msg = AsyncMock()
    msg.body = b'{"orderId":"123","amount":500.0}'
    msg.headers = {}
    msg.delivery_tag = 123
    msg.ack = AsyncMock()
    msg.nack = AsyncMock()
    msg.process = MagicMock()
    return msg


@pytest.fixture
def mock_amqp_channel():
    """Mock de canal AMQP (aio_pika.Channel)."""
    channel = AsyncMock()
    channel.basic_publish = AsyncMock()
    channel.basic_qos = AsyncMock()
    channel.declare_queue = AsyncMock()
    return channel


# ============================================================================
# Factory e fixtures de mensagens AMQP tipadas
# ============================================================================

def _build_amqp_message(
    body: bytes,
    *,
    message_id: str | None = None,
    event_type: str | None = None,
    routing_key: str = "order.created",
    headers: dict[str, Any] | None = None,
) -> MagicMock:
    """
    Constrói um MagicMock que imita aio_pika.IncomingMessage.

    O consumer usa a mensagem assim:
        async with message.process(requeue=False):
            event = OrderCreatedEvent.model_validate_json(message.body)

    Logo process() deve ser um async context manager.
    """
    msg = MagicMock()
    msg.body = body
    msg.message_id = message_id or str(uuid4())
    msg.type = event_type or "OrderCreatedEvent"
    msg.routing_key = routing_key
    msg.headers = headers or {}

    # process() como async context manager: "async with message.process(requeue=False):"
    process_cm = AsyncMock()
    process_cm.__aenter__ = AsyncMock(return_value=None)
    process_cm.__aexit__ = AsyncMock(return_value=None)
    msg.process = MagicMock(return_value=process_cm)

    return msg


@pytest.fixture
def make_amqp_message():
    """
    Fixture-factory: devolve a função _build_amqp_message para os testes
    construírem mensagens customizadas.

    Uso nos testes:
        message = make_amqp_message(body=b"...", message_id="abc")
    """
    return _build_amqp_message


@pytest.fixture
def valid_amqp_message(sample_order_created_event: OrderCreatedEvent) -> MagicMock:
    """
    Mensagem AMQP válida e pronta para uso — amount=500 → APPROVED.
    Serializada com by_alias=True para gerar os nomes que o consumer espera
    (eventId, orderId, createdAt).
    """
    payload = sample_order_created_event.model_dump_json(by_alias=True).encode()
    return _build_amqp_message(
        body=payload,
        message_id=sample_order_created_event.event_id,
        event_type="OrderCreatedEvent",
        routing_key="order.created",
    )


@pytest.fixture
def valid_amqp_message_high_amount(
    sample_order_created_event_high_amount: OrderCreatedEvent,
) -> MagicMock:
    """
    Mensagem AMQP válida — amount=1500 → REJECTED.
    """
    payload = sample_order_created_event_high_amount.model_dump_json(by_alias=True).encode()
    return _build_amqp_message(
        body=payload,
        message_id=sample_order_created_event_high_amount.event_id,
        event_type="OrderCreatedEvent",
        routing_key="order.created",
    )


# ============================================================================
# Contextos e Utilidades
# ============================================================================

@pytest.fixture
def trace_context_w3c():
    """Contexto de trace W3C padrão para propagação distribuída."""
    return "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


@pytest.fixture
def amqp_message_with_trace_context(mock_amqp_message, trace_context_w3c):
    """Mock de mensagem AMQP com contexto de trace W3C nos headers."""
    mock_amqp_message.headers = {
        "traceparent": trace_context_w3c.encode()
    }
    return mock_amqp_message


@pytest.fixture
def mock_connection():
    """Mock de conexão AMQP (aio_pika.abc.AbstractRobustConnection)."""
    connection = AsyncMock()
    connection.channel = AsyncMock()
    return connection