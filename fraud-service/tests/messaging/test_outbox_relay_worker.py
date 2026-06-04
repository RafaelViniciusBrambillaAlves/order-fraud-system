"""
Testes para OutboxRelayWorker.

Usa as fixtures do conftest.py (mock_outbox_repository) e define
fixtures locais para o canal/conexão AMQP, pois o mock_amqp_channel
do conftest é genérico demais para o worker.

Fixtures locais (sem conflito com o conftest):
  amqp_exchange   → exchange com .publish mockado
  amqp_channel    → canal com get_exchange + async context manager
  amqp_connection → conexão que devolve amqp_channel
  relay_worker    → instância real de OutboxRelayWorker
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika

from app.domain.entities.outbox_message import OutboxMessage
from app.domain.enums.outbox_status import OutboxStatus
from app.messaging.publishers.outbox_relay_worker import OutboxRelayWorker


# ---------------------------------------------------------------------------
# Helper — constrói OutboxMessage com estado forçado
# ---------------------------------------------------------------------------

def make_pending_message(
    exchange: str = "fraud.events",
    routing_key: str = "order.approved",
    payload: str = '{"order_id":"abc"}',
    retry_count: int = 0,
) -> OutboxMessage:
    msg = OutboxMessage.create(
        event_type="OrderAnalyzedEvent",
        payload=payload,
        exchange=exchange,
        routing_key=routing_key,
    )
    object.__setattr__(msg, "status", OutboxStatus.PENDING)
    object.__setattr__(msg, "retry_count", retry_count)
    return msg


# ---------------------------------------------------------------------------
# Fixtures locais — AMQP
# ---------------------------------------------------------------------------

@pytest.fixture()
def amqp_exchange():
    """Exchange com publish mockado."""
    exchange = AsyncMock()
    exchange.publish = AsyncMock()
    return exchange


@pytest.fixture()
def amqp_channel(amqp_exchange):
    """
    Canal AMQP compatível com o padrão do worker:
        async with await self._connection.channel() as channel:
            exchange = await channel.get_exchange(...)
    """
    channel = AsyncMock()
    channel.get_exchange = AsyncMock(return_value=amqp_exchange)
    channel.__aenter__ = AsyncMock(return_value=channel)
    channel.__aexit__ = AsyncMock(return_value=False)
    return channel


@pytest.fixture()
def amqp_connection(amqp_channel):
    """Conexão que devolve amqp_channel ao ser awaited."""
    conn = MagicMock()
    conn.channel = AsyncMock(return_value=amqp_channel)
    return conn


@pytest.fixture()
def relay_worker(mock_outbox_repository, amqp_connection):
    """Instância real de OutboxRelayWorker com dependências mockadas."""
    return OutboxRelayWorker(
        outbox_repository=mock_outbox_repository,
        connection=amqp_connection,
    )


# ---------------------------------------------------------------------------
# _process_batch — ciclo sem mensagens
# ---------------------------------------------------------------------------

class TestProcessBatchEmpty:

    @pytest.mark.asyncio
    async def test_queries_repository_with_limit_50(
        self, relay_worker, mock_outbox_repository
    ):
        """Worker deve consultar repositório com limit=50 em todo ciclo."""
        mock_outbox_repository.get_pending_async.return_value = []

        await relay_worker._process_batch()

        mock_outbox_repository.get_pending_async.assert_awaited_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_no_messages_does_not_open_channel(
        self, relay_worker, mock_outbox_repository, amqp_connection
    ):
        """Sem mensagens, nenhum canal AMQP deve ser aberto."""
        mock_outbox_repository.get_pending_async.return_value = []

        await relay_worker._process_batch()

        amqp_connection.channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_messages_does_not_call_save(
        self, relay_worker, mock_outbox_repository
    ):
        """Sem mensagens, save_async não deve ser chamado."""
        mock_outbox_repository.get_pending_async.return_value = []

        await relay_worker._process_batch()

        mock_outbox_repository.save_async.assert_not_awaited()


# ---------------------------------------------------------------------------
# _process_batch — publicação bem-sucedida
# ---------------------------------------------------------------------------

class TestProcessBatchSuccess:

    @pytest.mark.asyncio
    async def test_marks_message_as_sent(
        self, relay_worker, mock_outbox_repository
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        assert msg.status == OutboxStatus.SENT

    @pytest.mark.asyncio
    async def test_persists_message_after_publish(
        self, relay_worker, mock_outbox_repository
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        mock_outbox_repository.save_async.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_calls_exchange_publish_once(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        amqp_exchange.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publishes_with_correct_routing_key(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message(routing_key="order.rejected")
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        _, kwargs = amqp_exchange.publish.call_args
        assert kwargs.get("routing_key") == "order.rejected"

    @pytest.mark.asyncio
    async def test_amqp_message_body_matches_payload(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        payload = '{"order_id":"test-123"}'
        msg = make_pending_message(payload=payload)
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        published: aio_pika.Message = amqp_exchange.publish.call_args[0][0]
        assert published.body == payload.encode()

    @pytest.mark.asyncio
    async def test_amqp_message_delivery_mode_is_persistent(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        published: aio_pika.Message = amqp_exchange.publish.call_args[0][0]
        assert published.delivery_mode == aio_pika.DeliveryMode.PERSISTENT

    @pytest.mark.asyncio
    async def test_amqp_message_type_matches_event_type(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        await relay_worker._process_batch()

        published: aio_pika.Message = amqp_exchange.publish.call_args[0][0]
        assert published.type == msg.event_type

    @pytest.mark.asyncio
    async def test_all_messages_in_batch_are_published(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        messages = [make_pending_message() for _ in range(3)]
        mock_outbox_repository.get_pending_async.return_value = messages

        await relay_worker._process_batch()

        for msg in messages:
            assert msg.status == OutboxStatus.SENT
        assert amqp_exchange.publish.await_count == 3

    @pytest.mark.asyncio
    async def test_save_called_once_per_message(
        self, relay_worker, mock_outbox_repository
    ):
        messages = [make_pending_message() for _ in range(3)]
        mock_outbox_repository.get_pending_async.return_value = messages

        await relay_worker._process_batch()

        assert mock_outbox_repository.save_async.await_count == 3


# ---------------------------------------------------------------------------
# _process_batch — falha de publicação
# ---------------------------------------------------------------------------

class TestProcessBatchFailure:

    @pytest.mark.asyncio
    async def test_publish_failure_increments_retry_count(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("broker unavailable")

        await relay_worker._process_batch()

        assert msg.retry_count == 1

    @pytest.mark.asyncio
    async def test_publish_failure_records_last_error(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("connection reset")

        await relay_worker._process_batch()

        assert msg.last_error == "connection reset"

    @pytest.mark.asyncio
    async def test_publish_failure_still_persists_message(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        """save_async deve ser chamado no finally mesmo em caso de erro."""
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("timeout")

        await relay_worker._process_batch()

        mock_outbox_repository.save_async.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_message_becomes_failed_at_max_retries(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        """Na 5ª falha (retry_count=4 → 5), status deve mudar para FAILED."""
        msg = make_pending_message(retry_count=4)
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("final failure")

        await relay_worker._process_batch()

        assert msg.status == OutboxStatus.FAILED
        assert msg.retry_count == 5

    @pytest.mark.asyncio
    async def test_message_stays_pending_below_max_retries(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        """Abaixo do limite, status deve permanecer PENDING para permitir retry."""
        msg = make_pending_message(retry_count=2)
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("transient error")

        await relay_worker._process_batch()

        assert msg.status == OutboxStatus.PENDING

    @pytest.mark.asyncio
    async def test_failure_in_one_message_does_not_block_others(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        """Falha em uma mensagem não deve impedir o processamento das seguintes."""
        msg_fail = make_pending_message(routing_key="order.approved")
        msg_ok = make_pending_message(routing_key="order.rejected")
        mock_outbox_repository.get_pending_async.return_value = [msg_fail, msg_ok]
        amqp_exchange.publish.side_effect = [Exception("boom"), None]

        await relay_worker._process_batch()

        assert msg_fail.status == OutboxStatus.PENDING
        assert msg_ok.status == OutboxStatus.SENT


# ---------------------------------------------------------------------------
# _publish_message — injeção de trace context
# ---------------------------------------------------------------------------

class TestTraceContextInjection:

    @pytest.mark.asyncio
    async def test_inject_called_once_per_message(
        self, relay_worker, mock_outbox_repository
    ):
        messages = [make_pending_message(), make_pending_message()]
        mock_outbox_repository.get_pending_async.return_value = messages

        with patch(
            "app.messaging.publishers.outbox_relay_worker.inject_trace_context"
        ) as mock_inject:
            await relay_worker._process_batch()

        assert mock_inject.call_count == len(messages)

    @pytest.mark.asyncio
    async def test_inject_receives_a_dict(
        self, relay_worker, mock_outbox_repository
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]
        captured = []

        with patch(
            "app.messaging.publishers.outbox_relay_worker.inject_trace_context",
            side_effect=lambda h: captured.append(h),
        ):
            await relay_worker._process_batch()

        assert len(captured) == 1
        assert isinstance(captured[0], dict)


# ---------------------------------------------------------------------------
# run() — comportamento do loop principal
# ---------------------------------------------------------------------------

class TestRunLoop:

    @pytest.mark.asyncio
    async def test_cancelled_error_stops_loop(
        self, relay_worker, mock_outbox_repository
    ):
        """CancelledError deve ser re-lançado imediatamente."""
        mock_outbox_repository.get_pending_async.side_effect = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await relay_worker.run()

    @pytest.mark.asyncio
    async def test_amqp_connection_error_does_not_stop_loop(
        self, relay_worker, mock_outbox_repository
    ):
        """AMQPConnectionError deve ser capturado e o loop deve continuar."""
        call_count = 0

        async def side_effect(*_, **__):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise aio_pika.exceptions.AMQPConnectionError("refused")
            raise asyncio.CancelledError()

        mock_outbox_repository.get_pending_async.side_effect = side_effect

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(asyncio.CancelledError):
                await relay_worker.run()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_generic_exception_does_not_stop_loop(
        self, relay_worker, mock_outbox_repository
    ):
        """Exceções inesperadas devem ser logadas e o loop deve continuar."""
        call_count = 0

        async def side_effect(*_, **__):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("unexpected")
            raise asyncio.CancelledError()

        mock_outbox_repository.get_pending_async.side_effect = side_effect

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(asyncio.CancelledError):
                await relay_worker.run()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_sleeps_polling_interval_between_cycles(
        self, relay_worker, mock_outbox_repository
    ):
        """Worker deve dormir exatamente _POLLING_INTERVAL=1s entre ciclos."""
        call_count = 0

        async def side_effect(*_, **__):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()
            return []

        mock_outbox_repository.get_pending_async.side_effect = side_effect

        with patch(
            "app.messaging.publishers.outbox_relay_worker.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            with pytest.raises(asyncio.CancelledError):
                await relay_worker.run()

        mock_sleep.assert_awaited()
        sleep_arg = mock_sleep.call_args[0][0]
        assert sleep_arg == 1  # _POLLING_INTERVAL


# ---------------------------------------------------------------------------
# Métricas OpenTelemetry
# ---------------------------------------------------------------------------

class TestMetrics:

    @pytest.mark.asyncio
    async def test_published_counter_incremented_on_success(
        self, relay_worker, mock_outbox_repository
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]

        with patch(
            "app.messaging.publishers.outbox_relay_worker.fraud_metrics"
        ) as m:
            m.outbox_messages_published_total = MagicMock()
            m.outbox_messages_failed_total = MagicMock()
            m.outbox_relay_duration = MagicMock()
            m.publisher_duration = MagicMock()
            m.processing_errors_total = MagicMock()

            await relay_worker._process_batch()

        m.outbox_messages_published_total.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_counters_incremented_on_error(
        self, relay_worker, mock_outbox_repository, amqp_exchange
    ):
        msg = make_pending_message()
        mock_outbox_repository.get_pending_async.return_value = [msg]
        amqp_exchange.publish.side_effect = Exception("nack")

        with patch(
            "app.messaging.publishers.outbox_relay_worker.fraud_metrics"
        ) as m:
            m.outbox_messages_published_total = MagicMock()
            m.outbox_messages_failed_total = MagicMock()
            m.outbox_relay_duration = MagicMock()
            m.publisher_duration = MagicMock()
            m.processing_errors_total = MagicMock()

            await relay_worker._process_batch()

        m.outbox_messages_failed_total.add.assert_called_once()
        m.processing_errors_total.add.assert_called_once()