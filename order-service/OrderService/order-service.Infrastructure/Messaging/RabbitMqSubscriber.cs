using System;
using System.IO.Pipes;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using order_service.Application.Subscribers;
using Polly;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using RabbitMQ.Client.Exceptions;

/// Subscriber responsável por:
/// Conectar no RabbitMQ
/// Escutar filas
/// Receber mensagens
/// Executar o processamento
/// Enviar ACK/NACK (confirma o recebimento (ACK - Acknowledgement) ou relata um erro/falha (NACK - Negative Acknowledgement))
/// Recriar conexão caso o canal caia

namespace order_service.Infrastructure.Messaging;

public sealed class RabbitMqSubscriber : IEventSubscriber, IDisposable
{
    private IConnection? _connection;
    private IModel? _channel;
    private readonly RabbitMqSettings _settings;
    private readonly ILogger<RabbitMqSubscriber> _logger;
    private readonly object _lock = new();

    // Pipeline de retry
    // Tenta reconectar automaticamente em caso de falha
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

    public RabbitMqSubscriber(
        IOptions<RabbitMqSettings> options,
        ILogger<RabbitMqSubscriber> logger)
    {
        _settings = options.Value;
        _logger = logger;
        Connect();
    }

    // Cria conexão e canal com RabbitMQ
    private void Connect()
    {
        RetryPipeline.Execute(() => 
        {
            _logger.LogInformation(
                "Subscriber connecting to RabbitMQ at {Host}:{Port}",
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
                DispatchConsumersAsync = true
            };

            _connection = factory.CreateConnection("order-service-subscriber");

            // Cria canal de comunicação
            _channel = _connection.CreateModel();

            // Define quantas mensagens podem ser processadas ao mesmo tempo
            // prefetchCount = 1 => processa 1 por vez
            _channel.BasicQos(
                prefetchSize: 0, 
                prefetchCount: 1, 
                global: false);

            DeclareTopology();

            _logger.LogInformation("RabbitMQ subscriber connected");
        });
    }

    private void DeclareTopology()
    {
        if (_channel is null || _channel.IsClosed)
            throw new InvalidOperationException("Channel unavailable");

        // Exchanges 
        _channel.ExchangeDeclare(
            exchange: "fraud.events",
            type: ExchangeType.Direct,
            durable: true
        );

        // DLQ
        _channel.QueueDeclare(
            queue: "order.result.dlq",
            durable: true,
            exclusive: false,
            autoDelete: false
        );

        // Queue principal 
        _channel.QueueDeclare(
            queue: "order.result.queue",
            durable: true,
            exclusive: false,
            autoDelete: false,
            arguments: new Dictionary<string, object>
            {
                ["x-dead-letter-exchange"] = "",
                ["x-dead-letter-routing-key"] = "order.result.dlq",
                // ["x-message-ttl"] = 30000
            }
        );

        // Bindigs
        _channel.QueueBind(
            queue: "order.result.queue",
            exchange: "fraud.events",
            routingKey: "order.approved"
        );

        _channel.QueueBind(
            queue: "order.result.queue",
            exchange: "fraud.events",
            routingKey: "order.rejected"
        );

        _logger.LogInformation("Subscriber topology declared");
    }

    // Subscribe
    // Registra um consumer assincrono na fila informada
    public void Subscribe(string queue, Func<ReadOnlyMemory<byte>, CancellationToken, Task> handler)
    {   
        // Verifica se canal está aberto
        EnsureChannelIsOpen();

        var consumer = new AsyncEventingBasicConsumer(_channel);

        // Evento executado quando mensagem chega
        consumer.Received += async(_, eventArgs) =>
        {   
            // Identificador da mensagem
            var deliveryTag = eventArgs.DeliveryTag;

            try
            {
                _logger.LogDebug(
                    "Message received | Queue={Queue} DeliveryTag={Tag} RoutingKey={Key}",
                    queue, deliveryTag, eventArgs.RoutingKey);

                    // Executa processamento da mensagem
                    await handler(eventArgs.Body, CancellationToken.None);

                     // ACK = RabbitMQ remove mensagem da fila
                    _channel!.BasicAck(deliveryTag, multiple: false);

                    _logger.LogDebug(
                        "Message ACKed | Queue={Queue} DeliveryTag={Tag}", queue, deliveryTag);
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex,
                    "Error processing message | Queue={Queue} DeliveryTag={Tag}. Sending NACK -> DLQ.",
                    queue, deliveryTag);

                // NACK sem requeue
                // Mensagem vai para Dead Letter Queue
                _channel!.BasicNack(deliveryTag, multiple: false, requeue: false);
            }
        };
        
        // Inicia consumo da fila
        _channel!.BasicConsume(
            queue: queue,
            autoAck: false,
            consumerTag: $"order-service-{queue}-consumer",
            consumer: consumer);
        
        _logger.LogInformation(
            "Subscriber registered | Queue={Queue}", queue);

    }

    // Helpers
    // Verifica se canal está aberto
    private void EnsureChannelIsOpen()
    {
        if (_channel is not null && _channel.IsOpen)
            return;

        lock (_lock)
        {
            if (_channel is not null && _channel.IsOpen)
                return;

            _logger.LogWarning("Subscriber channel is closed. Reconnecting...");
            Connect();
        }
    }  

    // Libera recursos
    public void Dispose()
    {
        try
        {
            _channel?.Close();
            _channel?.Dispose();
            _connection?.Close();
            _connection?.Dispose();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disposing RabbitMQ subscriber");
        }
    } 
}
