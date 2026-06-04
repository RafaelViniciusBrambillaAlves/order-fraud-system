"""
Testes para a função analyze_order (lógica de negócio pura).

Testa a regra de análise de fraude:
- amount > 1000.0 → REJECTED
- amount ≤ 1000.0 → APPROVED
"""

import pytest
from app.application.use_cases.analyze_order import analyze_order
from app.domain.enums.fraud_status import FraudStatus
from app.schemas.order_created_event import OrderCreatedEvent
from uuid import uuid4
from datetime import datetime, timezone


class TestAnalyzeOrder:
    """Testes da função analyze_order com vários cenários."""

    def test_amount_below_threshold_returns_approved(self, sample_order_created_event):
        """Pedidos com valor abaixo do threshold (999.99) devem ser APPROVED."""
        # Arrange
        sample_order_created_event.amount = 999.99

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        assert result == FraudStatus.APPROVED

    def test_amount_equals_threshold_returns_approved(self, sample_order_created_event_at_threshold):
        """Pedidos com valor exatamente no threshold (1000.0) devem ser APPROVED."""
        # Arrange
        event = sample_order_created_event_at_threshold
        assert event.amount == 1000.0

        # Act
        result = analyze_order(event)

        # Assert
        assert result == FraudStatus.APPROVED

    def test_amount_above_threshold_returns_rejected(self, sample_order_created_event_high_amount):
        """Pedidos com valor acima do threshold (1000.01) devem ser REJECTED."""
        # Arrange
        event = sample_order_created_event_high_amount
        assert event.amount > 1000.0

        # Act
        result = analyze_order(event)

        # Assert
        assert result == FraudStatus.REJECTED

    def test_zero_amount_returns_approved(self, sample_order_created_event):
        """Pedidos com valor zero devem ser APPROVED (não é fraude)."""
        # Arrange
        sample_order_created_event.amount = 0.0

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        assert result == FraudStatus.APPROVED

    def test_negative_amount_returns_approved(self, sample_order_created_event):
        """Pedidos com valor negativo devem ser APPROVED (edge case, processado como devolução)."""
        # Arrange
        sample_order_created_event.amount = -500.0

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        # Assumindo que valores negativos também retornam APPROVED
        # (poderiam ser devoluções ou reembolsos)
        assert result == FraudStatus.APPROVED

    def test_very_large_amount_returns_rejected(self, sample_order_created_event):
        """Pedidos com valor muito alto (999999.99) devem ser REJECTED."""
        # Arrange
        sample_order_created_event.amount = 999999.99

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        assert result == FraudStatus.REJECTED

    def test_decimal_precision_just_above_threshold(self, sample_order_created_event):
        """Teste de precisão decimal: 1000.01 deve ser REJECTED."""
        # Arrange
        sample_order_created_event.amount = 1000.01

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        assert result == FraudStatus.REJECTED

    def test_decimal_precision_just_below_threshold(self, sample_order_created_event):
        """Teste de precisão decimal: 1000.00 (epsilon abaixo) deve ser APPROVED."""
        # Arrange
        sample_order_created_event.amount = 999.9999

        # Act
        result = analyze_order(sample_order_created_event)

        # Assert
        assert result == FraudStatus.APPROVED
