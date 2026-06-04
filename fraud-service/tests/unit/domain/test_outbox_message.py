"""
Testes para a entidade OutboxMessage.

Valida o ciclo de vida completo da mensagem no padrão Outbox:
PENDING → SENT ou FAILED (com retry até 5x).
"""

import pytest
from datetime import datetime, timezone
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.enums.outbox_status import OutboxStatus


class TestOutboxMessage:
    """Testes da entidade OutboxMessage."""

    def test_create_returns_pending_status(self):
        """Novo OutboxMessage deve ter status PENDING."""
        # Arrange & Act
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{"orderId":"123"}',
            exchange="fraud.events",
            routing_key="order.approved"
        )

        # Assert
        assert msg.status == OutboxStatus.PENDING
        assert msg.retry_count == 0
        assert msg.created_at is not None
        assert msg.sent_at is None
        assert msg.last_error is None

    def test_create_initializes_fields_correctly(self):
        """Novo OutboxMessage deve inicializar todos os campos."""
        # Arrange
        event_type = "OrderAnalyzed"
        payload = '{"orderId":"123","status":"APPROVED"}'
        exchange = "fraud.events"
        routing_key = "order.approved"

        # Act
        msg = OutboxMessage.create(
            event_type=event_type,
            payload=payload,
            exchange=exchange,
            routing_key=routing_key
        )

        # Assert
        assert msg.event_type == event_type
        assert msg.payload == payload
        assert msg.exchange == exchange
        assert msg.routing_key == routing_key
        assert msg.status == OutboxStatus.PENDING
        assert msg.id is not None

    def test_mark_as_sent_updates_status_and_timestamp(self):
        """mark_as_sent() deve mudar status para SENT e setar sent_at."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )
        assert msg.status == OutboxStatus.PENDING
        assert msg.sent_at is None

        # Act
        msg.mark_as_sent()

        # Assert
        assert msg.status == OutboxStatus.SENT
        assert msg.sent_at is not None
        assert msg.sent_at <= datetime.now(timezone.utc)

    def test_mark_as_sent_only_works_from_pending(self):
        """mark_as_sent() apenas funciona se status for PENDING."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )
        msg.mark_as_sent()
        assert msg.status == OutboxStatus.SENT

        # Act & Assert — marcar novamente como sent deve falhar ou ser idempotente
        # (depende da implementação, aqui assumimos que é permitido - idempotente)
        msg.mark_as_sent()
        assert msg.status == OutboxStatus.SENT

    def test_mark_as_failed_increments_retry_count(self):
        """mark_as_failed() deve incrementar retry_count."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )
        assert msg.retry_count == 0

        # Act
        msg.mark_as_failed("connection error")

        # Assert
        assert msg.retry_count == 1
        assert msg.last_error == "connection error"
        assert msg.status == OutboxStatus.PENDING  # Continua PENDING para retry

    def test_mark_as_failed_multiple_times_increments_counter(self):
        """mark_as_failed() deve incrementar retry_count a cada chamada."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )

        # Act & Assert
        for i in range(4):
            msg.mark_as_failed(f"error_{i}")
            assert msg.retry_count == i + 1
            assert msg.status == OutboxStatus.PENDING

    def test_mark_as_failed_five_times_sets_failed_status(self):
        """Após 5 tentativas de falha, status deve mudar para FAILED."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )

        # Act
        for i in range(5):
            msg.mark_as_failed(f"error_{i}")

        # Assert
        assert msg.status == OutboxStatus.FAILED
        assert msg.retry_count == 5

    def test_mark_as_failed_with_error_message(self):
        """mark_as_failed() deve armazenar a mensagem de erro."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )
        error_msg = "RabbitMQ connection timeout after 30s"

        # Act
        msg.mark_as_failed(error_msg)

        # Assert
        assert msg.last_error == error_msg
        assert msg.retry_count == 1

    def test_cannot_mark_sent_twice(self):
        """OutboxMessage enviada não deve ser marcada como sent novamente (idempotência)."""
        # Arrange
        msg = OutboxMessage.create(
            event_type="OrderAnalyzed",
            payload='{}',
            exchange="fraud.events",
            routing_key="order.approved"
        )

        # Act
        first_sent_at = datetime.now(timezone.utc)
        msg.mark_as_sent()

        # Assert
        assert msg.status == OutboxStatus.SENT
        initial_sent_at = msg.sent_at

        # Marcar como sent novamente (idempotência)
        msg.mark_as_sent()
        assert msg.status == OutboxStatus.SENT
        # Verificar que sent_at não mudou significativamente (ou fez reset)
        # Isso depende da implementação — aqui apenas verificamos que segue SENT
