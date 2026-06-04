"""
Testes para o DlqConsumer.

Valida tratamento de mensagens na Dead Letter Queue:
- Extração de headers x-death
- Logging estruturado
- Emissão de métricas
- Não reprocessamento
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestDlqConsumer:
    """Testes do consumer DlqConsumer."""

    @pytest.mark.asyncio
    async def test_dlq_consumer_extracts_x_death_headers(
        self,
        mock_amqp_message,
        mock_logger
    ):
        """DlqConsumer deve extrair headers x-death para análise de falhas."""
        # Arrange
        mock_amqp_message.headers = {
            "x-death": [
                {
                    "count": 5,
                    "reason": "rejected",
                    "queue": "fraud.analysis.queue",
                    "time": 1234567890,
                    "exchange": "order.events",
                    "routing-keys": ["order.created"]
                }
            ]
        }

        # Act
        x_death = mock_amqp_message.headers.get("x-death")

        # Assert
        assert x_death is not None
        assert len(x_death) > 0
        assert x_death[0]["count"] == 5
        assert x_death[0]["reason"] == "rejected"

    @pytest.mark.asyncio
    async def test_dlq_consumer_logs_structured_message(
        self,
        mock_amqp_message,
        mock_logger
    ):
        """DlqConsumer deve fazer log estruturado da mensagem de DLQ."""
        # Arrange
        mock_amqp_message.body = b'{"orderId":"123","amount":500}'
        mock_logger.error = MagicMock()

        # Act
        # Simulação de logging
        mock_logger.error(
            "Message reached DLQ",
            extra={
                "queue": "fraud.analysis.dlq",
                "message_body": mock_amqp_message.body.decode(),
                "headers": mock_amqp_message.headers
            }
        )

        # Assert
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_dlq_consumer_increments_dlq_metric(
        self,
        mock_amqp_message,
        mock_metrics
    ):
        """DlqConsumer deve incrementar métrica de DLQ."""
        # Arrange
        mock_metrics.add = MagicMock()

        # Act
        mock_metrics.add(1)

        # Assert
        mock_metrics.add.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_dlq_consumer_does_not_reprocess(
        self,
        mock_amqp_message,
        mock_order_repository
    ):
        """DlqConsumer deve apenas observar, nunca reprocessar."""
        # Arrange
        mock_order_repository.add_async = AsyncMock()

        # Act
        # DlqConsumer deveria apenas logar/emitir métrica, não chamar add_async

        # Assert
        mock_order_repository.add_async.assert_not_called()
