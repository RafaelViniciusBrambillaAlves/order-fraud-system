using System.Diagnostics;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using order_service.Application.Observability;
using order_service.Application.Subscribers;
using Polly;    
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using RabbitMQ.Client.Exceptions;
using OpenTelemetry.Trace;

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
        // Connect();
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

            _logger.LogInformation("RabbitMQ subscriber connected");
        });
    }

    // Subscribe
    // Registra um consumer assincrono na fila informada
    public void Subscribe(
        string queue, 
        Func    <ReadOnlyMemory<byte>, MessageMetadata, CancellationToken, Task> handler)
    {   
        // Verifica se canal está aberto
        var connected = EnsureChannelIsOpen();

        if (!connected || _channel is null)
        {
            _logger.LogWarning(
                "Skipping subscription for queue {Queue} because RabbitMQ is unavailable.",
                queue);

            return;
        }

        var consumer = new AsyncEventingBasicConsumer(_channel);

        // Evento executado quando mensagem chega
        consumer.Received += async(_, eventArgs) =>
        {   
            // Identificador da mensagem
            var deliveryTag = eventArgs.DeliveryTag;

            var parentContext = eventArgs.BasicProperties?.Headers
                .ExtractTraceContext();

            using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
                $"rabbitmq.consume {queue}",
                ActivityKind.Consumer,
                parentContext?.ActivityContext ?? default(ActivityContext));

            activity?.SetTag("messaging.system", "rabbitmq");
            activity?.SetTag("messaging.destination", queue);
            activity?.SetTag("messaging.operation", "receive");
            activity?.SetTag("messaging.rabbitmq.routing_key", eventArgs.RoutingKey);
            
            // Extrai metadados do header
            // MessageId é setado pelo RabbitMqPublisher em cada mensagem publicada.
            var messageId = eventArgs.BasicProperties?.MessageId;

            if (string.IsNullOrWhiteSpace(messageId))
            {
                messageId = Guid.NewGuid().ToString();

                _logger.LogWarning(
                    "Message without MessageId received | Queue={Queue} DeliveryTag={Tag}. " +
                    "Generated fallback EventId={EventId}. " +
                    "Ensure the publisher sets BasicProperties.MessageId.",
                    queue, deliveryTag, messageId);    
            }

            activity?.SetTag("messaging.message_id", messageId);

            var metadata = new MessageMetadata(
                EventId: messageId,
                EventType: eventArgs.BasicProperties?.Type ?? string.Empty,
                RoutingKey: eventArgs.RoutingKey);

            try
            {
                _logger.LogDebug(
                    "Message received | Queue={Queue} DeliveryTag={Tag} RoutingKey={Key}",
                    queue, deliveryTag, eventArgs.RoutingKey);

                // Executa processamento da mensagem
                await handler(eventArgs.Body, metadata, CancellationToken.None);

                    // ACK = RabbitMQ remove mensagem da fila
                _channel!.BasicAck(deliveryTag, multiple: false);

                _logger.LogDebug(
                    "Message ACKed | Queue={Queue} DeliveryTag={Tag}", queue, deliveryTag);
            }
            catch (Exception ex)
            {
                activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
                activity?.RecordException(ex);

                ApplicationTelemetry.OperationErrors.Add(1,
                    new KeyValuePair<string, object?>("operation", "rabbitmq.consume"),
                    new KeyValuePair<string, object?>("queue", queue));

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
    private bool EnsureChannelIsOpen()
    {
        if (_channel is not null && _channel.IsOpen)
            return true;

        lock (_lock)
        {
            if (_channel is not null && _channel.IsOpen)
                return true;

            try
            {
                _logger.LogWarning(
                    "Subscriber channel is closed. Trying reconnect...");

                Connect();

                return _channel is not null && _channel.IsOpen;
            }
            catch (Exception ex)
            {
                _logger.LogError(
                    ex,
                    "RabbitMQ unavailable. Subscriber will continue without connection.");

                return false;
            }
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
