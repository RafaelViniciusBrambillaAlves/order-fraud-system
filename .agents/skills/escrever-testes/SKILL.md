---
name: escrever-testes
description: >
  Use esta skill para escrever testes unitários, de integração ou de contrato
  para qualquer parte do sistema. Ativa quando o usuário pede para "testar",
  "escrever testes", "cobrir com testes", "adicionar testes unitários/integração".
  Funciona para order-service (.NET/xUnit) e fraud-service (Python/pytest).
---

# Skill: Escrever Testes

## Princípios gerais

- Teste comportamento, não implementação. O nome do teste deve descrever
  o cenário e o resultado esperado, não o nome do método.
- Padrão de nomenclatura: `Metodo_Cenario_ResultadoEsperado`
  Exemplo: `CreateAsync_ValidInput_ReturnsOrderViewModel`
- Arrange / Act / Assert — sempre separe visualmente as três fases.
- Um assert principal por teste. Asserts auxiliares são permitidos para setup de contexto.

---

## Testes para order-service (.NET / xUnit)

### Estrutura de projeto de testes

Se não existir, crie o projeto de testes:
```bash
dotnet new xunit -n order-service.Tests \
  -o order-service/OrderService/order-service.Tests
dotnet sln order-service/OrderService/OrderService.sln add \
  order-service/OrderService/order-service.Tests/order-service.Tests.csproj
```

Packages recomendados:
```xml
<PackageReference Include="xunit" Version="2.9.*" />
<PackageReference Include="Moq" Version="4.20.*" />
<PackageReference Include="FluentAssertions" Version="6.*" />
<PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="8.0.*" />
```

### Teste de domínio (sem dependências externas)

```csharp
public class OrderTests
{
    [Fact]
    public void UpdateStatus_WhenOrderIsApproved_ThrowsInvalidOperationException()
    {
        // Arrange
        var order = new Order("Produto X", 100m);
        order.UpdateStatus(OrderStatus.APPROVED);

        // Act
        var act = () => order.UpdateStatus(OrderStatus.REJECTED);

        // Assert
        act.Should().Throw<InvalidOperationException>()
           .WithMessage("*finalized*");
    }
}
```

### Teste de handler com Moq

```csharp
public class OrderAnalyzedEventHandlerTests
{
    private readonly Mock<IOrderRepository> _orderRepoMock = new();
    private readonly Mock<IInboxRepository> _inboxRepoMock = new();
    private readonly Mock<ILogger<OrderAnalyzedEventHandler>> _loggerMock = new();

    private OrderAnalyzedEventHandler CreateSut() =>
        new(_orderRepoMock.Object, _inboxRepoMock.Object, _loggerMock.Object);

    [Fact]
    public async Task HandleAsync_DuplicateEventId_ReturnsWithoutUpdatingOrder()
    {
        // Arrange
        var eventId = Guid.NewGuid().ToString();
        _inboxRepoMock.Setup(r => r.ExistsAsync(eventId, It.IsAny<CancellationToken>()))
                      .ReturnsAsync(true);

        var sut = CreateSut();
        var @event = new OrderAnalyzedEvent(Guid.NewGuid(), "approved", DateTime.UtcNow);

        // Act
        await sut.HandleAsync(@event, eventId);

        // Assert
        _orderRepoMock.Verify(r => r.GetByIdAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()), Times.Never);
    }
}
```

### Teste com banco In-Memory (repositório)

```csharp
public class OrderRepositoryTests
{
    private static OrderDbContext CreateContext(string dbName)
    {
        var options = new DbContextOptionsBuilder<OrderDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;
        return new OrderDbContext(options);
    }

    [Fact]
    public async Task GetByIdAsync_ExistingOrder_ReturnsOrder()
    {
        // Arrange
        await using var ctx = CreateContext(nameof(GetByIdAsync_ExistingOrder_ReturnsOrder));
        var order = new Order("Descrição", 500m);
        ctx.Orders.Add(order);
        await ctx.SaveChangesAsync();

        var repo = new OrderRepository(ctx);

        // Act
        var result = await repo.GetByIdAsync(order.Id);

        // Assert
        result.Should().NotBeNull();
        result!.Id.Should().Be(order.Id);
    }
}
```

---

## Testes para fraud-service (Python / pytest)

### Estrutura de diretório de testes

```
fraud-service/
└── tests/
    ├── __init__.py
    ├── conftest.py           ← fixtures compartilhadas
    ├── unit/
    │   ├── test_analyze_order.py
    │   ├── test_order_created_handler.py
    │   └── test_outbox_message.py
    └── integration/
        └── test_mongo_repositories.py
```

### conftest.py padrão

```python
# fraud-service/tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

@pytest.fixture
def mock_order_repository():
    repo = AsyncMock()
    repo.add_async = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo

@pytest.fixture
def mock_outbox_repository():
    repo = AsyncMock()
    repo.add_async = AsyncMock()
    return repo

@pytest.fixture
def mock_inbox_repository():
    repo = AsyncMock()
    repo.exists_async = AsyncMock(return_value=False)
    repo.add_async = AsyncMock()
    return repo

@pytest.fixture
def sample_order_created_event():
    from app.schemas.order_created_event import OrderCreatedEvent
    return OrderCreatedEvent(
        eventId=str(uuid4()),
        orderId=uuid4(),
        amount=500.0,
        createdAt=datetime.now(timezone.utc)
    )
```

### Teste de regra de negócio (use case)

```python
# fraud-service/tests/unit/test_analyze_order.py
import pytest
from app.application.use_cases.analyze_order import analyze_order
from app.domain.enums.fraud_status import FraudStatus

class TestAnalyzeOrder:
    def test_amount_below_threshold_returns_approved(self, sample_order_created_event):
        sample_order_created_event.amount = 999.99
        result = analyze_order(sample_order_created_event)
        assert result == FraudStatus.APPROVED

    def test_amount_above_threshold_returns_rejected(self, sample_order_created_event):
        sample_order_created_event.amount = 1000.01
        result = analyze_order(sample_order_created_event)
        assert result == FraudStatus.REJECTED

    def test_amount_exactly_at_threshold_returns_approved(self, sample_order_created_event):
        sample_order_created_event.amount = 1000.0
        result = analyze_order(sample_order_created_event)
        assert result == FraudStatus.APPROVED
```

### Teste de handler com mocks

```python
# fraud-service/tests/unit/test_order_created_handler.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_handle_order_created_persists_order_and_outbox(
    sample_order_created_event,
    mock_order_repository,
    mock_outbox_repository,
):
    from app.application.handlers.order_created_handler import handle_order_created

    mock_session = AsyncMock()

    await handle_order_created(
        event=sample_order_created_event,
        order_repository=mock_order_repository,
        outbox_repository=mock_outbox_repository,
        session=mock_session,
    )

    mock_order_repository.add_async.assert_called_once()
    mock_outbox_repository.add_async.assert_called_once()
```

### Teste de entidade de domínio

```python
# fraud-service/tests/unit/test_outbox_message.py
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.enums.outbox_status import OutboxStatus

class TestOutboxMessage:
    def test_create_returns_pending_status(self):
        msg = OutboxMessage.create("OrderCreated", "{}", "exchange", "routing.key")
        assert msg.status == OutboxStatus.PENDING
        assert msg.retry_count == 0

    def test_mark_as_sent_updates_status(self):
        msg = OutboxMessage.create("OrderCreated", "{}", "exchange", "routing.key")
        msg.mark_as_sent()
        assert msg.status == OutboxStatus.SENT
        assert msg.sent_at is not None

    def test_mark_as_failed_increments_retry_count(self):
        msg = OutboxMessage.create("OrderCreated", "{}", "exchange", "routing.key")
        msg.mark_as_failed("connection error")
        assert msg.retry_count == 1
        assert msg.last_error == "connection error"

    def test_mark_as_failed_five_times_sets_failed_status(self):
        msg = OutboxMessage.create("OrderCreated", "{}", "exchange", "routing.key")
        for i in range(5):
            msg.mark_as_failed("erro")
        assert msg.status == OutboxStatus.FAILED
```

---

## Após escrever os testes

Execute e certifique-se de que passam:

```bash
# .NET
dotnet test order-service/OrderService/OrderService.sln --verbosity normal

# Python
cd fraud-service && pytest tests/ -v --tb=short
```

Reporte quaisquer falhas com o traceback completo antes de considerar a tarefa concluída.