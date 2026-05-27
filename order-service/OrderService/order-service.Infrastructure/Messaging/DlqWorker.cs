using System;
using System.Threading.Channels;
using Azure.Core;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Polly;
using Polly.Retry;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using RabbitMQ.Client.Exceptions;
using System.Collections;
using System.Text;
using order_service.Application.Observability;
using System.Diagnostics;
using OpenTelemetry.Trace;


namespace order_service.Infrastructure.Messaging;

/// <summary>
/// Consome uma Dead Letter Queue, extrai os headers x-death injetados pelo RabbitMQ,
/// emite um log estruturado de nível Error para cada mensagem e envia ACK.
///
/// Span de observabilidade:
///   - Cada mensagem DLQ recebe um span com kind=Consumer.
///   - O span é marcado como Error porque DLQ é por definição um cenário de falha.
///   - Exceções no próprio processamento (ex: falha ao parsear headers) são registradas
///     como RecordException separado do erro de negócio da mensagem.
/// </summary>
public class DlqWorker : BackgroundService, IDisposable
{
    private IConnection? _connection;
    private IModel? _channel;
    private readonly RabbitMqSettings _settings;
    private readonly DlqWorkerOptions _options;
    private readonly ILogger<DlqWorker> _logger;
    private readonly object _lock = new();

    private static readonly ResiliencePipeline RetryPipeline = new ResiliencePipelineBuilder()
        .AddRetry(new RetryStrategyOptions
        {
            MaxRetryAttempts = 5,
            Delay = TimeSpan.FromSeconds(3),
            BackoffType = DelayBackoffType.Exponential,
            ShouldHandle = new PredicateBuilder()
                .Handle<BrokerUnreachableException>()
                .Handle<ConnectFailureException>()
                .Handle<InvalidOperationException>()        
        })
        .Build();

    public DlqWorker(
        IOptions<RabbitMqSettings> options,
        ILogger<DlqWorker> logger,
        DlqWorkerOptions workerOptions)
    {
        _settings = options.Value;
        _logger = logger;
        _options = workerOptions;
    }

    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation(
            "DlqWorker starting | Queue={Queue}",
            _options.Queue);
        
        Connect();
        StartConsuming();

        return Task.CompletedTask;
    }

    private void Connect()
    {
        RetryPipeline.Execute(() =>
        {
            _logger.LogInformation(
                "DlqWorker connecting to RabbitMQ | Queue={Queue} Host={Host}:{Port}",
                _options.Queue, _settings.Host, _settings.Port);
            
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

            _connection = factory.CreateConnection(
                $"order-service-dlq-{_options.Queue}");

            _channel = _connection.CreateModel();

            // processa uma mensagem por vez na DLQ
            _channel.BasicQos(prefetchSize: 0, prefetchCount: 1, global: false);

            _logger.LogInformation(
                "DlqWorker connected | Queue={Queue}",
                _options.Queue);

        });
    }

    private void StartConsuming()
    {
        if (_channel is null || !_channel.IsOpen)
        {
            _logger.LogWarning(
                "DlqWorker channel unavailable, skipping consumer registration | Queue={Queue}",
                _options.Queue);

            return;
        }

        var consumer = new AsyncEventingBasicConsumer(_channel);

        consumer.Received += async (_, eventArgs) =>
        {
            var deliveryTag = eventArgs.DeliveryTag;
            var sw = Stopwatch.StartNew();

            using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
                $"dlq.process {_options.Queue}",
                ActivityKind.Consumer);

            try
            {
                var dlqMessage = ExtractDlqMessage(eventArgs);

                activity?.SetTag("messaging.system", "rabbitmq");
                activity?.SetTag("messaging.destination", _options.Queue);
                activity?.SetTag("messaging.operation", "receive");
                activity?.SetTag("dlq.message_id", dlqMessage.MessageId);
                activity?.SetTag("dlq.event_type", dlqMessage.EventType);
                activity?.SetTag("dlq.source_queue", dlqMessage.SourceQueue);
                activity?.SetTag("dlq.routing_key", dlqMessage.RoutingKey);
                activity?.SetTag("dlq.death_reason", dlqMessage.DeathReason);
                activity?.SetTag("dlq.death_count", dlqMessage.DeathCount);
                activity?.SetTag("dlq.first_death_at", dlqMessage.FirstDeathAt.ToString("0"));

                // DLQ
                activity?.SetStatus(ActivityStatusCode.Error,
                    $"Dead letter: {dlqMessage.DeathReason} from {dlqMessage.SourceQueue}");

                // Métrica com tags para segmentar por tipo de falha
                ApplicationTelemetry.DlqMessagesReceived.Add(1,
                    new KeyValuePair<string, object?>("death_reason", dlqMessage.DeathReason),
                    new KeyValuePair<string, object?>("source_queue", dlqMessage.SourceQueue),
                    new KeyValuePair<string, object?>("event_type", dlqMessage.EventType));

                _logger.LogError(
                    "Dead letter message received | " +
                    "Queue={Queue} " +
                    "MessageId={MessageId} " +
                    "EventType={EventType} " +
                    "SourceQueue={SourceQueue} " +
                    "RoutingKey={RoutingKey} " +
                    "DeathReason={DeathReason} " +
                    "DeathCount={DeathCount} " +
                    "FirstDeathAt={FirstDeathAt} " +
                    "BodyPreview={BodyPreview}",
                    _options.Queue,
                    dlqMessage.MessageId,
                    dlqMessage.EventType,
                    dlqMessage.SourceQueue,
                    dlqMessage.RoutingKey,
                    dlqMessage.DeathReason,
                    dlqMessage.DeathCount,
                    dlqMessage.FirstDeathAt,
                    // Preview de até 512 chars do body para não explodir o log
                    TruncateBody(dlqMessage.Body, maxChars: 512));
                
                await OnDeadLetterReceivedAsync(dlqMessage);

                _channel.BasicAck(deliveryTag, multiple: false);

                ApplicationTelemetry.DlqProcessingDuration.Record(
                    sw.Elapsed.TotalMilliseconds,
                    new KeyValuePair<string, object?>("queue", _options.Queue),
                    new KeyValuePair<string, object?>("death_reason", dlqMessage.DeathReason));
            }
            catch (Exception ex)
            {
                sw.Stop();

                activity?.RecordException(ex);

                ApplicationTelemetry.OperationErrors.Add(1,
                    new KeyValuePair<string, object?>("operation", "dlq.process"),
                    new KeyValuePair<string, object?>("queue", _options.Queue));

                _logger.LogError(ex, 
                    "DlqWorker failed to process dead letter message | " +
                    "Queue={Queue} DeliveryTag={Tag}",
                    _options.Queue, deliveryTag);

                _channel!.BasicNack(deliveryTag, multiple: false, requeue: true);
            }
        };
        _channel.BasicConsume(
            queue: _options.Queue,
            autoAck: false,
            consumerTag: $"order-service-dlq-{_options.Queue}-consumer",
            consumer: consumer);
        
        _logger.LogInformation(
            "DlqWorker consumer registered | Queue={Queue}",
            _options.Queue);
    }

    // Extrai os headers x-death injetados pelo RabbitMQ.
    // O RabbitMQ adiciona uma lista chamada "x-death" nos headers.
    // Cada entrada da lista é um dicionário com as chaves:
    //   - "queue" > fila de origem
    //   - "reason" > motivo (rejected, expired, maxlen, delivery-limit)
    //   - "count" > número de vezes que a mensagem morreu
    //   - "time" > timestamp da morte (AmqpTimestamp)
    //   - "exchange" > exchange de origem
    //   - "routing-keys" > lista de routing keys originais
    private DlqMessage ExtractDlqMessage(BasicDeliverEventArgs eventArgs)
    {
        var props = eventArgs.BasicProperties;

        var messageId = props?.MessageId ?? Guid.NewGuid().ToString();
        var eventType = props?.Type ?? "unknown";
        var routingKey = eventArgs.RoutingKey;

        var sourceQueue = "unknown";
        var deathReason  = "unknown";
        long deathCount  = 0;
        var firstDeathAt = DateTimeOffset.UtcNow;

        // Extrai x-death - pode ser nulo se o RabbitMQ não injetou headers
        if (props?.Headers is not null && 
            props.Headers.TryGetValue("x-death", out var xDeathRaw) &&
            xDeathRaw is IList xDeathList &&
            xDeathList.Count > 0 &&
            xDeathList[0] is IDictionary<string, object> firstDeath)
        {
            sourceQueue = ReadString(firstDeath, "queue");
            deathReason = ReadString(firstDeath, "reason");
            deathCount = ReadLong(firstDeath, "count");

            if (firstDeath.TryGetValue("time", out var timeRaw) &&
                timeRaw is AmqpTimestamp amqpTs)
            {
                firstDeathAt = DateTimeOffset.FromUnixTimeSeconds(amqpTs.UnixTime);
            }
        }

        return new DlqMessage(
            MessageId: messageId,
            EventType: eventType,
            SourceQueue: sourceQueue,
            RoutingKey: routingKey,
            DeathReason: deathReason,
            DeathCount: deathCount,
            FirstDeathAt: firstDeathAt,
            Body: eventArgs.Body
        );  
    }

    // Hook virtual para extensão 
    // para integrar com sistemas externos (Slack, Sentry, PagerDuty).
    protected virtual Task OnDeadLetterReceivedAsync(DlqMessage message) => Task.CompletedTask;

    //  Helpers para leitura segura dos headers
    private static string ReadString(IDictionary<string, object> dict, string key)
    {
        if (!dict.TryGetValue(key, out var val)) 
            return "unknown";

        return val switch
        {
            byte[] bytes => Encoding.UTF8.GetString(bytes),
            string s => s,
            _ => val.ToString() ?? "unknown"
        };
    }

    private static long ReadLong(IDictionary<string, object> dict, string key)
    {
        if (!dict.TryGetValue(key, out var val))
            return 0;

        return val switch
        {
            long l => l,
            int i => i,
            _ => 0
        };
    }

    private static string TruncateBody(ReadOnlyMemory<byte> body, int maxChars)
    {
        var text = Encoding.UTF8.GetString(body.Span);
        return text.Length <= maxChars
            ? text 
            : string.Concat(text.AsSpan(0, maxChars), "...");
    }

    public override void Dispose()
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
            _logger.LogError(ex, 
                "Error disposing DlqWorker | Queue={Queue}", 
                _options.Queue);
        }

        base.Dispose();
    }

}
