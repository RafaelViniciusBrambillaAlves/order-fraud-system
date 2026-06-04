"""
Testes para o handler order_created_handler.

Valida a orquestração completa do fluxo: análise + persistência + Outbox.
Testa padrões Inbox, Outbox, transações e observabilidade.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4
from app.application.handlers.order_created_handler import handle_order_created
from app.domain.enums.fraud_status import FraudStatus
from app.domain.enums.outbox_status import OutboxStatus


class TestOrderCreatedHandler:
    """Testes do handler order_created_handler."""

    @pytest.mark.asyncio
    async def test_handle_order_created_success_path(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Fluxo bem-sucedido: análise + persistência + Outbox."""
        # Arrange
        sample_order_created_event.amount = 500.0

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Verifica que Order foi persistida
        mock_order_repository.add_async.assert_called_once()
        # Verifica que OutboxMessage foi criada
        mock_outbox_repository.add_async.assert_called_once()


    @pytest.mark.asyncio
    async def test_handle_order_created_creates_order_with_approved_status(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Pedido abaixo do threshold deve ter status APPROVED."""
        # Arrange
        sample_order_created_event.amount = 500.0

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Assert
        # Captura o Order que foi persistido
        call_args = mock_order_repository.add_async.call_args
        order = call_args[0][0]
        assert order.fraud_status == FraudStatus.APPROVED

    @pytest.mark.asyncio
    async def test_handle_order_created_creates_order_with_rejected_status(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Pedido acima do threshold deve ter status REJECTED."""
        # Arrange
        sample_order_created_event.amount = 1500.0

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Assert
        call_args = mock_order_repository.add_async.call_args
        order = call_args[0][0]
        assert order.fraud_status == FraudStatus.REJECTED

    @pytest.mark.asyncio
    async def test_handle_order_created_persists_outbox_message(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """OutboxMessage deve ser persistida atomicamente com Order (Outbox Pattern)."""

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Assert
        mock_outbox_repository.add_async.assert_called_once()
        call_args = mock_outbox_repository.add_async.call_args
        outbox_msg = call_args[0][0]
        assert outbox_msg.status == OutboxStatus.PENDING
        assert outbox_msg.exchange == "fraud.events"
        assert outbox_msg.routing_key in ["order.approved", "order.rejected"]


    @pytest.mark.asyncio
    async def test_handle_order_created_passes_session_to_repositories(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Todas as operações devem usar a mesma sessão MongoDB (atomicidade)."""

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Assert
        # Todas as chamadas devem ter session=mock_session
        for call_item in mock_order_repository.add_async.call_args_list:
            assert call_item[1].get('session') == mock_session

    @pytest.mark.asyncio
    async def test_handle_order_created_handles_repository_error(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Erro em repositório deve ser propagado."""
        mock_order_repository.add_async.side_effect = Exception("DB connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="DB connection failed"):
            await handle_order_created(
                event=sample_order_created_event,
                order_repository=mock_order_repository,
                outbox_repository=mock_outbox_repository,
                session=mock_session
            )

    @pytest.mark.asyncio
    async def test_handle_order_created_order_has_correct_event_data(
        self,
        sample_order_created_event,
        mock_order_repository,
        mock_outbox_repository,
        mock_session
    ):
        """Order deve ter order_id e amount do evento."""
        # Arrange
        sample_order_created_event.amount = 750.0

        # Act
        await handle_order_created(
            event=sample_order_created_event,
            order_repository=mock_order_repository,
            outbox_repository=mock_outbox_repository,
            session=mock_session
        )

        # Assert
        call_args = mock_order_repository.add_async.call_args
        order = call_args[0][0]
        assert order.order_id == sample_order_created_event.order_id
        assert order.amount == sample_order_created_event.amount
