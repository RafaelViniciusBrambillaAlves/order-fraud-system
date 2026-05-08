using System;
using System.ComponentModel.DataAnnotations;

namespace order_service.Infrastructure.Messaging;

public class RabbitMqSettings
{
    public const string SectionName = "RabbitMq";

    [Required]
    public string Host { get; set; } = string.Empty;

    [Required]
    public int Port { get; set; } = 5672;

    [Required]
    public string Username { get; set; } = string.Empty;

    [Required]
    public string Password { get; set; } = string.Empty;

    // Exchanges
    public string OrderEventsExchange { get; set; } = "order.events";

    // Routing keys  
    public string OrderCreatedRoutingKey { get; set; } = "order.created";
}
