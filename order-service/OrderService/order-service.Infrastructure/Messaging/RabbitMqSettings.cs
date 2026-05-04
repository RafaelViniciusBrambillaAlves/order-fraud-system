using System;

namespace order_service.Infrastructure.Messaging;

public class RabbitMqSettings
{
    public const string SectionName = "RabbitMq";

    public string Host { get; set; } = "localhost";
    public int Port { get; set; } = 5672;
    public string Username { get; set; } = "guest";
    public string Password { get; set; } = "guest";

    // Exchanges
    public string OrderEventsExchange { get; set; } = "order.events";

    // Routing keys  
    public string OrderCreatedRoutingKey { get; set; } = "order.created";
}
