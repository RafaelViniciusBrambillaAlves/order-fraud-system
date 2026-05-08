using System.ComponentModel;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
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
                .Handle<IOException>()
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
        lock (_lock){
            DisposeConnection();

            RetryPipeline.Execute(() =>
            {
                _logger.LogInformation(
                    "Connecting to RabbitMQ at {Host}:{Port}",
                    _settings.Host,
                    _settings.Port);
                
                var factory = new ConnectionFactory
                {
                    HostName = _settings.Host,
                    Port = _settings.Port,
                    UserName = _settings.Username,
                    Password = _settings.Password,
                    AutomaticRecoveryEnabled = true,
                    NetworkRecoveryInterval = TimeSpan.FromSeconds(10),
                    RequestedHeartbeat = TimeSpan.FromSeconds(60)
                };

                _connection = factory.CreateConnection("order-servce-publish");

                _channel = _connection.CreateModel();

                _channel.ConfirmSelect();

                _logger.LogInformation("RabbitMQ publisher connected.");
            });
        }
    }

    // Publish
    public Task PublishAsync<TEvent>(
        TEvent @event,
        string exchange,
        string routingKey,
        CancellationToken cancellationToken = default)
        where TEvent : class
    {
       var payload = JsonSerializer.Serialize(@event, JsonOptions);

       var body = Encoding.UTF8.GetBytes(payload);

       return PublishBytesAsync(
        body,
        exchange,
        routingKey,
        typeof(TEvent).Name,
        cancellationToken);
    }

    public Task PublishAsync(
        string payload,
        string exchange,
        string routingKey,
        CancellationToken cancellationToken = default)
    {
        var body = Encoding.UTF8.GetBytes(payload);
        
        return PublishBytesAsync(
            body,
            exchange,
            routingKey,
            "outbox",
            cancellationToken);
    }

    private Task PublishBytesAsync(
        byte[] body,
        string exchange,
        string routingKey,
        string eventType,
        CancellationToken cancellationToken = default)
    {
        EnsureChannelIsOpen();
        
        lock (_lock)
        {
            var properties = _channel!.CreateBasicProperties();

            properties.ContentType = "application/json";
            properties.DeliveryMode = 2;
            properties.MessageId = Guid.NewGuid().ToString();
            properties.Timestamp = 
                new AmqpTimestamp(DateTimeOffset.UtcNow.ToUnixTimeSeconds());

            properties.Type = eventType;
            properties.AppId = "order-service";

            try
            {
                _channel.BasicPublish(
                    exchange: exchange,
                    routingKey: routingKey,
                    mandatory: false,
                    basicProperties: properties,
                    body: body);
                
                var confirmed = 
                    _channel.WaitForConfirms(TimeSpan.FromSeconds(5));

                if (!confirmed)
                {
                    throw new Exception(
                        $"Broker did not confirm message. Exchange={exchange} RoutingKey={routingKey}");
                }

                _logger.LogInformation(
                     "Published | Exchange={Exchange} RoutingKey={RoutingKey} Type={Type}",
                    exchange,
                    routingKey,
                    eventType);

            }
            catch (Exception ex)
            {
                _logger.LogInformation(
                    ex,
                    "Error publishing message | Exchange={Exchange} RoutingKey={RoutingKey}",
                    exchange,
                    routingKey);

                throw;
            }
        }

        return Task.CompletedTask;
    }

    private void EnsureChannelIsOpen()
    {
        if (_channel is not null && _channel.IsOpen)
            return;

        _logger.LogWarning("RabbitMQ channel closed. Reconnecting...");

        Connect();
    }

    // Dispose
    public void DisposeConnection()
    {
        try
        {
            if (_channel is not null)
            {
                if (_channel.IsOpen)
                    _channel.Close();

                _channel.Dispose();
                _channel = null;
            }

            if (_connection is not null)
            {
                if (_connection.IsOpen)
                    _connection.Close();
                
                _connection.Dispose();
                _connection = null;
            } 
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disposing RabbitMQ publisher.");
        }
    }

    public void Dispose()
    {
        DisposeConnection();
    }
}