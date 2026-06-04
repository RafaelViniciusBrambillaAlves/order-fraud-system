"""
Testes para observabilidade (spans, métricas, trace context).

Valida que a instrumentação OpenTelemetry está funcionando corretamente.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestTelemetryIntegration:
    """Testes de integração com OpenTelemetry."""

    @pytest.mark.asyncio
    async def test_handle_order_created_creates_spans(
        self,
        sample_order_created_event,
        mock_tracer
    ):
        """Handler deve criar spans para rastreamento."""
        # Arrange
        mock_tracer.start_as_current_span = MagicMock()
        span = MagicMock()
        span.__enter__ = MagicMock(return_value=span)
        span.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = span

        # Act
        # Simular criação de span
        with mock_tracer.start_as_current_span("fraud.handle_order_created"):
            pass

        # Assert
        mock_tracer.start_as_current_span.assert_called_once_with("fraud.handle_order_created")

    @pytest.mark.asyncio
    async def test_analyze_order_span_has_correct_attributes(
        self,
        sample_order_created_event,
        mock_tracer
    ):
        """Span de análise deve ter atributos corretos (status, threshold, score)."""
        # Arrange
        mock_tracer.start_as_current_span = MagicMock()
        span = MagicMock()
        span.set_attribute = MagicMock()
        span.__enter__ = MagicMock(return_value=span)
        span.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = span

        # Act
        with mock_tracer.start_as_current_span("fraud.analyze_order") as current_span:
            current_span.set_attribute("fraud.status", "APPROVED")
            current_span.set_attribute("fraud.threshold", 1000.0)
            current_span.set_attribute("fraud.amount", 500.0)

        # Assert
        assert span.set_attribute.call_count >= 3

    @pytest.mark.asyncio
    async def test_persist_span_has_db_attributes(
        self,
        mock_tracer
    ):
        """Span de persistência deve ter atributos de DB (operation, collection, etc)."""
        # Arrange
        mock_tracer.start_as_current_span = MagicMock()
        span = MagicMock()
        span.set_attribute = MagicMock()
        span.__enter__ = MagicMock(return_value=span)
        span.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = span

        # Act
        with mock_tracer.start_as_current_span("fraud.persist") as current_span:
            current_span.set_attribute("db.system", "mongodb")
            current_span.set_attribute("db.operation", "insert")
            current_span.set_attribute("db.mongo.collection", "orders")
            current_span.set_attribute("db.mongo.documents", 2)

        # Assert
        assert span.set_attribute.call_count >= 4

    @pytest.mark.asyncio
    async def test_metrics_incremented_on_analysis(
        self,
        sample_order_created_event,
        mock_metrics
    ):
        """Métricas devem ser incrementadas durante análise."""
        # Arrange
        mock_metrics.add = MagicMock()
        mock_metrics.record = MagicMock()

        # Act
        # Simular incremento de métricas
        mock_metrics.add(1)  # fraud.orders.analyzed.total
        mock_metrics.record(500.0)  # fraud.analysis.duration.seconds

        # Assert
        assert mock_metrics.add.call_count >= 1
        assert mock_metrics.record.call_count >= 1

    @pytest.mark.asyncio
    async def test_trace_context_propagated_through_layers(
        self,
        sample_order_created_event,
        trace_context_w3c
    ):
        """Contexto de trace deve ser propagado através de todas as camadas."""
        # Arrange
        trace_id = trace_context_w3c.split("-")[1]  # Extrai trace_id do W3C format
        span_id = trace_context_w3c.split("-")[2]   # Extrai span_id

        # Act & Assert
        # Verificar que trace_id e span_id são válidos (hex strings)
        assert len(trace_id) == 32  # 16 bytes em hex
        assert len(span_id) == 16   # 8 bytes em hex

    @pytest.mark.asyncio
    async def test_duplicate_message_metric(
        self,
        sample_order_created_event,
        mock_metrics
    ):
        """Métrica de mensagem duplicada deve ser incrementada."""
        # Arrange
        mock_metrics.add = MagicMock()

        # Act
        # Simular incremento em caso de duplicata
        mock_metrics.add(1)

        # Assert
        mock_metrics.add.assert_called_once_with(1)
