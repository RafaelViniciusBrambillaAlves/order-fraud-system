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
using order_service.Application.Observability;
using System.Diagnostics;
using order_service.Application.Services;
using OpenTelemetry.Trace;

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
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            $"rabbitmq.publish {exchange}/{routingKey}",
            ActivityKind.Producer);
        
        activity?.SetTag("messaging.system", "rabbitmq");
        activity?.SetTag("messaging.destination", exchange);
        activity?.SetTag("messaging.destination_kind", "exchange");
        activity?.SetTag("messaging.rabbitmq.routing_key", routingKey);
        activity?.SetTag("messaging.operation", "publish" );
        activity?.SetTag("messaging.event_type", eventType);
        activity?.SetTag("messaging.message.body.size", body.Length);

        var connected  = EnsureChannelIsOpen();
        
        if (!connected || _channel is null)
        {
            const string conErr = "RabbitMQ channel unavailable — message not published";

            activity?.SetStatus(ActivityStatusCode.Error, conErr);

            ApplicationTelemetry.OperationErrors.Add(1, 
                new KeyValuePair<string, object?>("operation", "publish"),
                new KeyValuePair<string, object?>("exchange", exchange));

            throw new InvalidOperationException(conErr);
        }

        var sw = Stopwatch.StartNew();

        lock (_lock)
        {
            var properties = _channel!.CreateBasicProperties();

            properties.ContentType = "application/json";
            properties.DeliveryMode = 2;
            properties.MessageId = Guid.NewGuid().ToString();
            properties.Timestamp = new AmqpTimestamp(DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            properties.Type = eventType;
            properties.AppId = ApplicationTelemetry.ServiceName;

            // OTEL: injeta
            // Conecta o trace do publisher com o consumer, mesmo que
            // a mensagem fique na fila por horas antes de ser consumida.
            properties.InjectTraceContext();

            activity?.SetTag("messaging.message_id", properties.MessageId);

            try
            {       
                _channel.BasicPublish(
                    exchange: exchange,
                    routingKey: routingKey,
                    mandatory: false,
                    basicProperties: properties,
                    body: body);
                
                var confirmed = _channel.WaitForConfirms(TimeSpan.FromSeconds(5));

                if (!confirmed)
                {
                    activity?.SetStatus(ActivityStatusCode.Error, "Broker did not confirm message");
                    throw new Exception(
                        $"Broker did not confirm message. Exchange={exchange} RoutingKey={routingKey}");
                }

                sw.Stop();

                activity?.SetTag("messaging.confirmed", true);
                activity?.SetStatus(ActivityStatusCode.Ok);

                // Histograma de latencia de publicacao
                ApplicationTelemetry.PublisherDuration.Record(
                    sw.Elapsed.TotalSeconds,
                    new KeyValuePair<string, object?>("exchange", exchange),
                    new KeyValuePair<string, object?>("routing_key", routingKey),
                    new KeyValuePair<string, object?>("result", "success"));


                _logger.LogInformation(
                    "Published Message | Exchange={Exchange} RoutingKey={RoutingKey} EventType={eventType}" + 
                    "MessageId={MessageId} DurationMs={DurationMs:F1}",
                    exchange,
                    routingKey,
                    eventType, 
                    properties.MessageId,
                    sw.Elapsed.TotalMilliseconds);

            }
            catch (Exception ex)
            {
                activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
                activity?.RecordException(ex);

                ApplicationTelemetry.OperationErrors.Add(1, 
                    new KeyValuePair<string, object?>("operation", "publish"),
                    new KeyValuePair<string, object?>("exchange", exchange));

                ApplicationTelemetry.PublisherDuration.Record(
                    sw.Elapsed.TotalSeconds,
                    new KeyValuePair<string, object?>("exchange", exchange),
                    new KeyValuePair<string, object?>("routing_key", routingKey),
                    new KeyValuePair<string, object?>("result", "error"));

                _logger.LogError(
                    ex,
                    "Error publishing message | Exchange={Exchange} RoutingKey={RoutingKey}" + 
                    "EventType={EventType} DurationMs={DurationMs:F1}",
                    exchange,
                    routingKey, 
                    eventType,
                    sw.Elapsed.TotalMilliseconds);

                throw;
            }
        }

        return Task.CompletedTask;
    }

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
                _logger.LogWarning("RabbitMQ unavailable. Subscriber will continue without connection.");
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

    public void Dispose() => DisposeConnection();
}