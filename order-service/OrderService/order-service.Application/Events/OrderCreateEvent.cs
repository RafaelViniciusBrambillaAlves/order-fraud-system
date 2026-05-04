namespace order_service.Application.Events;

// Evento publicado no RabbitMQ após persistência do pedido.
// Contrato imutável - nunca remova propriedades, apenas adicione.

public sealed record OrderCreatedEvent(
    Guid OrderId,
    decimal Amount, 
    string Description,
    DateTime CreatedAt
)
{
    public const string EventName = "OrderCreated";
} 

