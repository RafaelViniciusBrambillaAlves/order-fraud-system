"""
tests/integration/test_end_to_end_flow.py

Testes E2E do fraud-service.

O ponto de entrada real é OrderCreatedConsumer._on_message, que orquestra:
  1. Desserialização da mensagem AMQP
  2. Abertura de sessão MongoDB + transação (via mongo_client.start_session)
  3. Verificação de idempotência via InboxRepository — inbox check
  4. handle_order_created → análise de fraude + persistência de order + outbox
  5. Persistência do InboxMessage para garantir idempotência futura

Os testes injetam doubles nos repositórios e simulam a sessão MongoDB,
mas exercitam o caminho completo de código sem pular nenhuma camada.

Cobertura:
  ✅ Fluxo feliz — amount baixo  → APPROVED, routing_key correto
  ✅ Fluxo feliz — amount alto   → REJECTED, routing_key correto
  ✅ Limite exato do threshold   → 1000.0 resulta em APPROVED (regra é > 1000)
  ✅ Um centavo acima            → 1000.01 resulta em REJECTED
  ✅ Idempotência                → evento duplicado é silenciosamente ignorado
  ✅ Redelivery                  → segunda entrega não reprocessa
  ✅ Persistência atômica        → order, outbox e inbox usam a mesma sessão
  ✅ Ordem de persistência       → inbox é salvo por último
  ✅ Mensagem malformada         → exceção propagada, nada é persistido
  ✅ Campos obrigatórios faltando → ValidationError, nada é persistido
  ✅ Falha no repositório        → InboxMessage não é registrado
  ✅ Contrato do OutboxMessage   → payload JSON válido, exchange, event_type corretos
  ✅ Routing key parametrizado   → cinco amounts verificam a fronteira do threshold
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.domain.enums.fraud_status import FraudStatus
from app.domain.enums.outbox_status import OutboxStatus
from app.messaging.consumers.order_created_consumer import OrderCreatedConsumer
from app.schemas.order_created_event import OrderCreatedEvent


# ---------------------------------------------------------------------------
# Sentinel — compara igual a qualquer valor (evita importar unittest.mock.ANY
# para não confundir com o ANY do pytest em asserções de keyword args)
# ---------------------------------------------------------------------------

class _ANY:
    """Sentinela local: igual a qualquer objeto."""

    def __eq__(self, other: object) -> bool:
        return True

    def __repr__(self) -> str:
        return "<ANY>"


ANY = _ANY()


# ---------------------------------------------------------------------------
# Helper: constrói o consumer com os doubles injetados
# A conexão AMQP é mockada porque não chamamos start() — apenas _on_message.
# ---------------------------------------------------------------------------

def _make_consumer(
    mock_mongo_client: AsyncMock,
    mock_order_repository: AsyncMock,
    mock_outbox_repository: AsyncMock,
    mock_inbox_repository: AsyncMock,
) -> OrderCreatedConsumer:
    return OrderCreatedConsumer(
        connection=AsyncMock(),
        mongo_client=mock_mongo_client,
        order_repository=mock_order_repository,
        outbox_repository=mock_outbox_repository,
        inbox_repository=mock_inbox_repository,
    )


# ---------------------------------------------------------------------------
# Helper: extrai o kwarg `session` de uma chamada AsyncMock de forma segura
# ---------------------------------------------------------------------------

def _session_from_call(mock: AsyncMock) -> object:
    """
    Retorna o valor do kwarg 'session' da última chamada do mock.
    Lança AssertionError descritivo se o kwarg não estiver presente.
    """
    call_kwargs = mock.call_args[1] if mock.call_args[1] else {}
    assert "session" in call_kwargs, (
        f"Esperava kwarg 'session' em {mock}, mas a chamada foi: {mock.call_args}"
    )
    return call_kwargs["session"]


# ---------------------------------------------------------------------------
# Fixture local: consumer pronto para uso em todos os testes desta suíte
# ---------------------------------------------------------------------------

@pytest.fixture()
def consumer(
    mock_mongo_client: AsyncMock,
    mock_order_repository: AsyncMock,
    mock_outbox_repository: AsyncMock,
    mock_inbox_repository: AsyncMock,
) -> OrderCreatedConsumer:
    return _make_consumer(
        mock_mongo_client,
        mock_order_repository,
        mock_outbox_repository,
        mock_inbox_repository,
    )


# ===========================================================================
# TestEndToEndFlowApproved
# ===========================================================================

class TestEndToEndFlowApproved:
    """Pedidos com amount <= 1000 devem ser aprovados."""

    @pytest.mark.asyncio
    async def test_full_flow_approved(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        sample_order_created_event: OrderCreatedEvent,
    ) -> None:
        """
        Fluxo completo com amount=500.
        Verifica cada passo da orquestração do consumer.
        """
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message)

        # 1. inbox check ocorreu com o event_id correto
        mock_inbox_repository.exists_async.assert_awaited_once_with(
            sample_order_created_event.event_id,
            session=ANY,
        )

        # 2. order foi persistida com fraud_status e order_id corretos
        mock_order_repository.add_async.assert_awaited_once()
        persisted_order = mock_order_repository.add_async.call_args[0][0]
        assert persisted_order.fraud_status == FraudStatus.APPROVED
        assert persisted_order.order_id == sample_order_created_event.order_id

        # 3. outbox criada com routing_key, exchange e status corretos
        mock_outbox_repository.add_async.assert_awaited_once()
        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.routing_key == "order.approved"
        assert outbox_msg.exchange == "fraud.events"
        assert outbox_msg.status == OutboxStatus.PENDING

        # 4. payload do outbox contém os campos que o order-service espera
        payload = json.loads(outbox_msg.payload)
        assert payload["fraud_status"] == FraudStatus.APPROVED
        assert str(sample_order_created_event.order_id) in outbox_msg.payload

        # 5. InboxMessage registrado com o event_id correto
        mock_inbox_repository.add_async.assert_awaited_once()
        inbox_arg = mock_inbox_repository.add_async.call_args[0][0]
        assert inbox_arg.event_id == sample_order_created_event.event_id

    @pytest.mark.asyncio
    async def test_boundary_amount_exactly_at_threshold_is_approved(
        self,
        consumer: OrderCreatedConsumer,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        sample_order_created_event_at_threshold: OrderCreatedEvent,
        make_amqp_message,
    ) -> None:
        """
        amount=1000.0 exatamente no threshold → APPROVED.
        A regra de rejeição é amount > 1000, portanto 1000 não rejeita.
        """
        mock_inbox_repository.exists_async.return_value = False
        message = make_amqp_message(
            body=sample_order_created_event_at_threshold.model_dump_json(by_alias=True).encode(),
            message_id=sample_order_created_event_at_threshold.event_id,
        )

        await consumer._on_message(message)

        persisted_order = mock_order_repository.add_async.call_args[0][0]
        assert persisted_order.fraud_status == FraudStatus.APPROVED

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.routing_key == "order.approved"


# ===========================================================================
# TestEndToEndFlowRejected
# ===========================================================================

class TestEndToEndFlowRejected:
    """Pedidos com amount > 1000 devem ser rejeitados."""

    @pytest.mark.asyncio
    async def test_full_flow_rejected(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message_high_amount: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        sample_order_created_event_high_amount: OrderCreatedEvent,
    ) -> None:
        """Fluxo completo com amount=1500 → REJECTED, todos os artefatos corretos."""
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message_high_amount)

        # order
        persisted_order = mock_order_repository.add_async.call_args[0][0]
        assert persisted_order.fraud_status == FraudStatus.REJECTED
        assert persisted_order.order_id == sample_order_created_event_high_amount.order_id

        # outbox
        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.routing_key == "order.rejected"
        assert outbox_msg.exchange == "fraud.events"
        assert outbox_msg.status == OutboxStatus.PENDING
        assert json.loads(outbox_msg.payload)["fraud_status"] == FraudStatus.REJECTED

        # inbox
        mock_inbox_repository.add_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_one_cent_above_threshold_is_rejected(
        self,
        consumer: OrderCreatedConsumer,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        order_id: UUID,
        event_id: str,
        make_amqp_message,
    ) -> None:
        """amount=1000.01 → REJECTED (um centavo acima do threshold)."""
        mock_inbox_repository.exists_async.return_value = False

        event = OrderCreatedEvent(
            event_id=event_id,
            order_id=order_id,
            amount=1000.01,
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        message = make_amqp_message(
            body=event.model_dump_json(by_alias=True).encode(),
            message_id=event_id,
        )

        await consumer._on_message(message)

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.routing_key == "order.rejected"


# ===========================================================================
# TestEndToEndIdempotency
# ===========================================================================

class TestEndToEndIdempotency:
    """Inbox Pattern — garantia de idempotência via event_id."""

    @pytest.mark.asyncio
    async def test_duplicate_event_is_silently_ignored(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """
        event_id já presente no inbox (exists_async → True):
        nada deve ser persistido e a mensagem deve ser ACK'd normalmente.
        """
        mock_inbox_repository.exists_async.return_value = True

        await consumer._on_message(valid_amqp_message)

        mock_order_repository.add_async.assert_not_awaited()
        mock_outbox_repository.add_async.assert_not_awaited()
        mock_inbox_repository.add_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redelivery_after_first_success_is_ignored(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """
        Simula redelivery do broker:
        primeira entrega processa normalmente, segunda é ignorada.
        """
        # Primeira entrega
        mock_inbox_repository.exists_async.return_value = False
        await consumer._on_message(valid_amqp_message)

        assert mock_order_repository.add_async.await_count == 1
        assert mock_outbox_repository.add_async.await_count == 1

        # Segunda entrega (mesmo event_id já está no inbox)
        mock_inbox_repository.exists_async.return_value = True
        await consumer._on_message(valid_amqp_message)

        assert mock_order_repository.add_async.await_count == 1, (
            "order não deve ser persistida novamente em redelivery"
        )
        assert mock_outbox_repository.add_async.await_count == 1, (
            "outbox não deve ser criada novamente em redelivery"
        )


# ===========================================================================
# TestEndToEndAtomicPersistence
# ===========================================================================

class TestEndToEndAtomicPersistence:
    """
    Verifica a atomicidade garantida pela sessão MongoDB.
    Order, outbox e inbox devem compartilhar a mesma sessão para que
    a transação possa ser revertida em caso de falha parcial.
    """

    @pytest.mark.asyncio
    async def test_all_writes_use_the_same_session(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        mock_session: MagicMock,
    ) -> None:
        """
        order_repository, outbox_repository e inbox_repository devem todos
        receber a mesma instância de sessão MongoDB.
        """
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message)

        order_session = _session_from_call(mock_order_repository.add_async)
        outbox_session = _session_from_call(mock_outbox_repository.add_async)
        inbox_session = _session_from_call(mock_inbox_repository.add_async)

        assert order_session is mock_session, "order deve usar a sessão aberta pelo consumer"
        assert outbox_session is mock_session, "outbox deve usar a sessão aberta pelo consumer"
        assert inbox_session is mock_session, "inbox deve usar a sessão aberta pelo consumer"

    @pytest.mark.asyncio
    async def test_inbox_is_persisted_last(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """
        InboxMessage deve ser salvo APÓS order e outbox.
        Se o inbox fosse salvo antes e a persistência de negócio falhasse,
        o event_id ficaria marcado como processado sem ter sido processado.
        """
        mock_inbox_repository.exists_async.return_value = False
        call_order: list[str] = []

        def make_tracker(name: str): 
            async def tracker(*args, **kwargs) -> None: 
                call_order.append(name)
            return tracker
        
        mock_order_repository.add_async.side_effect = make_tracker("order")
        mock_outbox_repository.add_async.side_effect = make_tracker("outbox")
        mock_inbox_repository.add_async.side_effect = make_tracker("inbox")

        await consumer._on_message(valid_amqp_message)

        assert call_order, (
            "Nenhum repositório foi chamado — verifique se os mocks estão injetados corretamente"
        )

        assert call_order[-1] == "inbox", (
            f"InboxMessage deve ser o último a ser persistido. "
            f"Ordem observada: {call_order}"
        )
        assert "order" in call_order, "order deve ser persistida"
        assert "outbox" in call_order, "outbox deve ser persistida"


# ===========================================================================
# TestEndToEndErrorHandling
# ===========================================================================

class TestEndToEndErrorHandling:
    """
    Cenários de falha.
    Em todos os casos o consumer deve propagar a exceção para que o
    aio_pika envie NACK e a mensagem seja roteada para a DLQ.
    """

    @pytest.mark.asyncio
    async def test_malformed_json_raises_and_does_not_persist(
        self,
        consumer: OrderCreatedConsumer,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        make_amqp_message,
    ) -> None:
        """JSON inválido → exceção, nenhuma escrita no banco."""
        message = make_amqp_message(body=b"{ not valid json }")

        with pytest.raises(Exception):
            await consumer._on_message(message)

        mock_order_repository.add_async.assert_not_awaited()
        mock_outbox_repository.add_async.assert_not_awaited()
        mock_inbox_repository.add_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_required_fields_raises_and_does_not_persist(
        self,
        consumer: OrderCreatedConsumer,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        make_amqp_message,
    ) -> None:
        """
        Payload com campos obrigatórios ausentes (orderId e eventId faltando)
        → ValidationError do Pydantic, nenhuma escrita.
        """
        incomplete_payload = json.dumps({"amount": 100.0}).encode()
        message = make_amqp_message(body=incomplete_payload)

        with pytest.raises(Exception):
            await consumer._on_message(message)

        mock_order_repository.add_async.assert_not_awaited()
        mock_outbox_repository.add_async.assert_not_awaited()
        mock_inbox_repository.add_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_order_repository_failure_does_not_register_inbox(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """
        Falha em order_repository.add_async → InboxMessage NÃO deve ser salvo.
        Garante que o próximo redelivery será processado normalmente
        (event_id não está marcado como processado).
        """
        mock_inbox_repository.exists_async.return_value = False
        mock_order_repository.add_async.side_effect = RuntimeError("DB unavailable")

        with pytest.raises(RuntimeError, match="DB unavailable"):
            await consumer._on_message(valid_amqp_message)

        mock_inbox_repository.add_async.assert_not_awaited()


# ===========================================================================
# TestEndToEndOutboxContract
# ===========================================================================

class TestEndToEndOutboxContract:
    """
    Verifica o contrato público do OutboxMessage gerado pelo handler.
    Esses campos são consumidos pelo order-service via RabbitMQ.
    """

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_required_fields(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        sample_order_created_event: OrderCreatedEvent,
    ) -> None:
        """
        Payload deve ser JSON válido com order_id e fraud_status —
        campos que o order-service usa para atualizar o status do pedido.
        """
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message)

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        payload = json.loads(outbox_msg.payload)

        assert "order_id" in payload, "order_id ausente no payload do outbox"
        assert "fraud_status" in payload, "fraud_status ausente no payload do outbox"
        assert payload["order_id"] == str(sample_order_created_event.order_id)

    @pytest.mark.asyncio
    async def test_outbox_exchange_is_fraud_events(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """Exchange deve ser sempre 'fraud.events'."""
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message)

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.exchange == "fraud.events"

    @pytest.mark.asyncio
    async def test_outbox_event_type_is_order_analyzed_event(
        self,
        consumer: OrderCreatedConsumer,
        valid_amqp_message: MagicMock,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
    ) -> None:
        """event_type deve ser 'OrderAnalyzedEvent' para que o consumer do order-service deserialize corretamente."""
        mock_inbox_repository.exists_async.return_value = False

        await consumer._on_message(valid_amqp_message)

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.event_type == "OrderAnalyzedEvent"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount, expected_routing_key",
        [
            (0.01,    "order.approved"),   # mínimo possível
            (999.99,  "order.approved"),   # justo abaixo do threshold
            (1000.0,  "order.approved"),   # exatamente no threshold (não rejeita)
            (1000.01, "order.rejected"),   # um centavo acima
            (9999.99, "order.rejected"),   # bem acima do threshold
        ],
        ids=[
            "min_amount",
            "just_below_threshold",
            "exactly_at_threshold",
            "one_cent_above_threshold",
            "well_above_threshold",
        ],
    )
    async def test_routing_key_matches_fraud_decision(
        self,
        consumer: OrderCreatedConsumer,
        mock_order_repository: AsyncMock,
        mock_outbox_repository: AsyncMock,
        mock_inbox_repository: AsyncMock,
        order_id: UUID,
        event_id: str,
        make_amqp_message,
        amount: float,
        expected_routing_key: str,
    ) -> None:
        """
        Parametrizado: routing_key do outbox deve refletir corretamente
        a decisão de fraude para diferentes valores de amount.
        """
        mock_inbox_repository.exists_async.return_value = False
        mock_order_repository.add_async.reset_mock()
        mock_outbox_repository.add_async.reset_mock()

        event = OrderCreatedEvent(
            event_id=event_id,
            order_id=order_id,
            amount=amount,
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        message = make_amqp_message(
            body=event.model_dump_json(by_alias=True).encode(),
            message_id=event_id,
        )

        await consumer._on_message(message)

        outbox_msg = mock_outbox_repository.add_async.call_args[0][0]
        assert outbox_msg.routing_key == expected_routing_key, (
            f"amount={amount} → esperava routing_key='{expected_routing_key}', "
            f"recebeu '{outbox_msg.routing_key}'"
        )