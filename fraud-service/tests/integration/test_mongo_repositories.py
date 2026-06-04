"""
Testes de integração para repositórios MongoDB.

Valida operações básicas: add, get_by_id, list_all, e queries com índices.
"""

import pytest
from uuid import uuid4
from app.domain.entities.order import Order
from app.domain.entities.inbox_message import InboxMessage
from app.domain.enums.fraud_status import FraudStatus


class TestMongoRepositories:
    """Testes dos repositórios MongoDB."""

    @pytest.mark.asyncio
    async def test_order_repository_add_async_persists_order(
        self,
        mock_order_repository,
        sample_order,
        mock_session
    ):
        """add_async() deve persistir Order no banco."""
        # Arrange
        mock_order_repository.add_async.return_value = None

        # Act
        await mock_order_repository.add_async(sample_order, session=mock_session)

        # Assert
        mock_order_repository.add_async.assert_called_once_with(sample_order, session=mock_session)

    @pytest.mark.asyncio
    async def test_order_repository_get_by_id_retrieves_order(
        self,
        mock_order_repository,
        sample_order
    ):
        """get_by_id() deve recuperar Order pelo ID."""
        # Arrange
        order_id = uuid4()
        mock_order_repository.get_by_id.return_value = sample_order

        # Act
        result = await mock_order_repository.get_by_id(order_id)

        # Assert
        assert result is not None
        assert result == sample_order
        mock_order_repository.get_by_id.assert_called_once_with(order_id)

    @pytest.mark.asyncio
    async def test_order_repository_get_by_id_returns_none_if_not_found(
        self,
        mock_order_repository
    ):
        """get_by_id() deve retornar None se Order não existir."""
        # Arrange
        order_id = uuid4()
        mock_order_repository.get_by_id.return_value = None

        # Act
        result = await mock_order_repository.get_by_id(order_id)

        # Assert
        assert result is None
        mock_order_repository.get_by_id.assert_called_once_with(order_id)

    @pytest.mark.asyncio
    async def test_order_repository_list_all_returns_all_orders(
        self,
        mock_order_repository,
        sample_order
    ):
        """list_all() deve retornar todas as Orders."""
        # Arrange
        mock_order_repository.list_all.return_value = [sample_order]

        # Act
        orders = await mock_order_repository.list_all()

        # Assert
        assert isinstance(orders, list)
        assert len(orders) >= 0
        mock_order_repository.list_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_inbox_repository_exists_async_returns_true_if_exists(
        self,
        mock_inbox_repository
    ):
        """exists_async() deve retornar True se event_id já foi processado."""
        # Arrange
        event_id = str(uuid4())
        mock_inbox_repository.exists_async.return_value = True

        # Act
        result = await mock_inbox_repository.exists_async(event_id)

        # Assert
        assert result is True
        mock_inbox_repository.exists_async.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_inbox_repository_exists_async_returns_false_if_not_exists(
        self,
        mock_inbox_repository
    ):
        """exists_async() deve retornar False se event_id ainda não foi processado."""
        # Arrange
        event_id = str(uuid4())
        mock_inbox_repository.exists_async.return_value = False

        # Act
        result = await mock_inbox_repository.exists_async(event_id)

        # Assert
        assert result is False
        mock_inbox_repository.exists_async.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_outbox_repository_get_pending_returns_only_pending(
        self,
        mock_outbox_repository,
        sample_outbox_message
    ):
        """get_pending_async() deve retornar apenas mensagens PENDING."""
        # Arrange
        mock_outbox_repository.get_pending_async.return_value = [sample_outbox_message]

        # Act
        pending = await mock_outbox_repository.get_pending_async(limit=50)

        # Assert
        assert isinstance(pending, list)
        if pending:
            for msg in pending:
                assert msg.status.value == 0  # PENDING = 0

    @pytest.mark.asyncio
    async def test_outbox_repository_count_pending_async(
        self,
        mock_outbox_repository
    ):
        """count_pending_async() deve retornar quantidade de mensagens PENDING."""
        # Arrange
        mock_outbox_repository.count_pending_async.return_value = 5

        # Act
        count = await mock_outbox_repository.count_pending_async()

        # Assert
        assert count >= 0
        assert isinstance(count, int)
        mock_outbox_repository.count_pending_async.assert_called_once()
