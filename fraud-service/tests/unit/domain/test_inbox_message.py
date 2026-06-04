"""
Testes para a entidade InboxMessage.

Valida a funcionalidade de rastreamento de eventos processados (Inbox Pattern).
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from app.domain.entities.inbox_message import InboxMessage


class TestInboxMessage:
    """Testes da entidade InboxMessage."""

    def test_create_returns_inbox_message_with_event_id(self):
        """Novo InboxMessage deve ter event_id."""
        # Arrange
        event_id = str(uuid4())

        # Act
        msg = InboxMessage.create(event_id=event_id)

        # Assert
        assert msg.event_id == event_id
        assert msg.id is not None
        assert msg.processed_at is not None

    def test_inbox_message_has_processed_at_timestamp(self):
        """InboxMessage deve registrar timestamp de processamento."""
        # Arrange
        event_id = str(uuid4())
        before = datetime.now(timezone.utc)

        # Act
        msg = InboxMessage.create(event_id=event_id)

        # Assert
        after = datetime.now(timezone.utc)
        assert msg.processed_at is not None
        assert before <= msg.processed_at <= after

    def test_inbox_message_event_id_is_stored(self):
        """InboxMessage deve armazenar event_id para verificação de duplicatas."""
        # Arrange
        event_id = str(uuid4())

        # Act
        msg1 = InboxMessage.create(event_id=event_id)
        msg2 = InboxMessage.create(event_id=event_id)

        # Assert
        assert msg1.event_id == msg2.event_id
        assert msg1.event_id == event_id
        # IDs são únicos, mas event_id pode ser igual (para verificação)
        assert msg1.id != msg2.id
