using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using order_service.Application.Publishers;
using Polly;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using RabbitMQ.Client.Exceptions;

namespace order_service.Infrastructure.Messaging;

public sealed class RabbitMqPublisher : IEventPublisher, IDisposable
{
    private IConnection? _connection;
    private IModel? _channel;
    private readonly RabbitMqSettings _settings;
    private readonly ILogger<RabbitMqPublisher> _logger;
    private readonly object _lock = new();

    // Flag para detectar mensagens não roteadas (mandatory: true)
    private bool _lastMessageReturned;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    private static readonly ResiliencePipeline RetryPipeline = new ResiliencePipelineBuilder()
        .AddRetry(new Polly.Retry.RetryStrategyOptions
        {
            MaxRetryAttempts = 5,
            Delay = TimeSpan.FromSeconds(2),
            BackoffType = DelayBackoffType.Exponential,
            ShouldHandle = new PredicateBuilder()
                .Handle<BrokerUnreachableException>()
                .Handle<ConnectFailureException>()
                .Handle<InvalidOperationException>()
        })
        .Build();

    public RabbitMqPublisher(
        IOptions<RabbitMqSettings> options,
        ILogger<RabbitMqPublisher> logger)
    {
        _settings = options.Value;
        _logger = logger;
        Connect();
    }

    // Conexão
    private void Connect()
    {
        RetryPipeline.Execute(() =>
        {
            _logger.LogInformation(
                "Connecting to RabbitMQ at {Host}:{Port}...",
                _settings.Host, _settings.Port);

            var factory = new ConnectionFactory
            {
                HostName = _settings.Host,
                Port = _settings.Port,
                UserName = _settings.Username,
                Password = _settings.Password,
                AutomaticRecoveryEnabled = true,
                NetworkRecoveryInterval = TimeSpan.FromSeconds(10),
                RequestedHeartbeat = TimeSpan.FromSeconds(60),
                DispatchConsumersAsync = false
            };

            _connection = factory.CreateConnection("order-service-publisher");
            _channel = _connection.CreateModel();

            // Publisher Confirms - broker confirma recebimento
            _channel.ConfirmSelect();

            // BasicReturn - captura mensagens não roteadas (mandatory: true)
            _channel.BasicReturn += OnBasicReturn;

            _logger.LogInformation("RabbitMQ connected.");
            DeclareTopology();
        });
    }

    // Topology
    private void DeclareTopology()
    {
        if (_channel is null || _channel.IsClosed)
            throw new InvalidOperationException("Channel unavailable.");

        // Exchanges
        _channel.ExchangeDeclare("order.events", ExchangeType.Direct, durable: true);
        _channel.ExchangeDeclare("fraud.events", ExchangeType.Direct, durable: true);

        // DLQs (sem argumentos - filas simples de erro)
        _channel.QueueDeclare("fraud.analysis.dlq", durable: true, exclusive: false, autoDelete: false);
        _channel.QueueDeclare("order.result.dlq", durable: true, exclusive: false, autoDelete: false);

        var fraudQueueArgs = new Dictionary<string, object>
        {
            { "x-dead-letter-exchange", "" },
            { "x-dead-letter-routing-key", "fraud.analysis.dlq" },
            // { "x-message-ttl", 30_000 } // 30 segundos
        }; 

        // Filas principais com DLQ configurada
        _channel.QueueDeclare(
            queue: "fraud.analysis.queue",
            durable: true,
            exclusive: false,
            autoDelete: false,
            arguments: fraudQueueArgs
        );

        _channel.QueueDeclare(
            queue: "order.result.queue",
            durable: true,
            exclusive: false,
            autoDelete: false,
            arguments: new Dictionary<string, object>
            {
                ["x-dead-letter-exchange"] = "",
                ["x-dead-letter-routing-key"] = "order.result.dlq",
                // ["x-message-ttl"] = 30_000
            });

        // Bindings
        _channel.QueueBind("fraud.analysis.queue", "order.events", "order.created");
        _channel.QueueBind("order.result.queue", "fraud.events", "order.approved");
        _channel.QueueBind("order.result.queue", "fraud.events", "order.rejected");

        _logger.LogInformation("RabbitMQ topology declared.");
    }


    // Publish
    public Task PublishAsync<TEvent>(
        TEvent @event,
        string exchange,
        string routingKey,
        CancellationToken cancellationToken = default)
        where TEvent : class
    {
        EnsureChannelIsOpen();

        var body = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(@event, JsonOptions));

        lock (_lock)
        {
            // Cria properties DENTRO do lock - canal garantido
            var properties = _channel!.CreateBasicProperties();
            properties.ContentType = "application/json";
            properties.DeliveryMode = 2;  // persistent
            properties.MessageId = Guid.NewGuid().ToString();
            properties.Timestamp = new AmqpTimestamp(DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            properties.Type = typeof(TEvent).Name;
            properties.AppId = "order-service";

            // Reset da flag antes de publicar
            _lastMessageReturned = false;

            _channel.BasicPublish(
                exchange: exchange,
                routingKey:  routingKey,
                mandatory: true,   // RabbitMQ devolve se não houver binding
                basicProperties: properties,
                body: body);

            // Aguarda confirmação do broker (ack/nack)
            var confirmed = _channel.WaitForConfirms(TimeSpan.FromSeconds(5));

            if (!confirmed)
                throw new Exception(
                    $"Broker did not confirm delivery. Exchange={exchange} RoutingKey={routingKey}");

            // BasicReturn é assíncrono - pequena espera para o evento chegar
            // Solução simples e suficiente para produção sem overhead de async
            Thread.Sleep(50);

            if (_lastMessageReturned)
                throw new Exception(
                    $"Message returned (no binding). Exchange={exchange} RoutingKey={routingKey}");
        }

        _logger.LogInformation(
            "Published | Exchange={Exchange} RoutingKey={RoutingKey} Type={Type}",
            exchange, routingKey, typeof(TEvent).Name);

        return Task.CompletedTask;
    }

    // Handlers internos

    private void OnBasicReturn(object? sender, BasicReturnEventArgs e)
    {
        _logger.LogError(
            "Message RETURNED (unroutable) | Exchange={Exchange} RoutingKey={RoutingKey} ReplyText={Reply}",
            e.Exchange, e.RoutingKey, e.ReplyText);

        // Sinaliza pro PublishAsync que a mensagem não foi roteada
        _lastMessageReturned = true;
    }

    private void EnsureChannelIsOpen()
    {
        if (_channel is not null && _channel.IsOpen)
            return;

        lock (_lock)
        {
            if (_channel is not null && _channel.IsOpen)
                return;

            _logger.LogWarning("Channel is closed. Reconnecting...");
            Connect();
        }
    }

    // Dispose
    public void Dispose()
    {
        try
        {
            if (_channel is not null)
            {
                _channel.BasicReturn -= OnBasicReturn;
                _channel.Close();
                _channel.Dispose();
            }

            _connection?.Close();
            _connection?.Dispose();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disposing RabbitMQ publisher.");
        }
    }
}