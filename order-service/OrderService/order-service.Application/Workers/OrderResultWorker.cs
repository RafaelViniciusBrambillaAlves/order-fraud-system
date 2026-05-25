using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using order_service.Application.Events;
using order_service.Application.Handlers;
using order_service.Application.Subscribers;
using Microsoft.Extensions.Hosting;
using System.Diagnostics;
using order_service.Application.Observability;
using OpenTelemetry.Trace;

namespace order_service.Application.Workers;

public sealed class OrderResultWorker : BackgroundService
{
    // Nome da fila que será consumida
    private const string Queue = "order.result.queue";

    private readonly IEventSubscriber _subscriber;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<OrderResultWorker> _logger;

    // Configuração do Json para ignorar diferença entre maiúsculas/minúsculas
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public OrderResultWorker(
        IEventSubscriber subscriber,
        IServiceScopeFactory scopeFactory,
        ILogger<OrderResultWorker> logger)
    {
        _subscriber = subscriber;
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    // Método executado automaticamente quando o Worker inicia
    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation(
            "{Worker} starting. Listening on queue '{Queue}'.",
            nameof(OrderResultWorker), Queue);
        
        _subscriber.Subscribe(Queue, (body, metadata, ct) => 
            DispatchAsync(body, metadata, ct));

        return Task.CompletedTask;
    }

    // Processa a mensagem recebida
    private async Task DispatchAsync(
        ReadOnlyMemory<byte> body, 
        MessageMetadata metadata,
        CancellationToken cancellationToken)
    {   
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            $"worker.consume {Queue}", 
            ActivityKind.Consumer);
        
        activity?.SetTag("messaging.system", "rabbitmq");
        activity?.SetTag("messaging.destination", Queue);
        activity?.SetTag("messaging.operation", "process");
        activity?.SetTag("messaging.message_id", metadata.EventId);
        activity?.SetTag("worker.step", "dispatch");
        activity?.SetTag("message.payload.size", body.Length);

        var sw = Stopwatch.StartNew();

        try
        {   
            // Converte bytes para JSON string
            var json = Encoding.UTF8.GetString(body.Span);

            // Converte JSON para objeto C#
            var @event = JsonSerializer.Deserialize<OrderAnalyzedEvent>(json, JsonOptions);
                
            if (@event is null)
            {   
                // Payload nulo após desserialização é uma mensagem malformada.
                // Lança exceção para que o RabbitMqSubscriber envie NACK
                // e a mensagem seja roteada para order.result.dlq.
                throw new InvalidOperationException(
                    $"Deserialization returned null | Queue={Queue} EventId={metadata.EventId} " +
                    $"Body={Encoding.UTF8.GetString(body.Span)}");
            }

            activity?.SetTag("order.id", @event.OrderId.ToString());
            activity?.SetTag("fraud.status", @event.FraudStatus);
            activity?.SetTag("worker.deserialized",   true);

            await using var scope = _scopeFactory.CreateAsyncScope();

            var handler = scope.ServiceProvider
                .GetRequiredService<OrderAnalyzedEventHandler>();

            await handler.HandleAsync(
                @event, 
                metadata.EventId, 
                cancellationToken);

            sw.Stop();

            activity?.SetTag("worker.duration.seconds", sw.Elapsed.TotalSeconds);
            activity?.SetStatus(ActivityStatusCode.Ok);

            _logger.LogInformation(
                "OrderAnalyzedEvent processed successfully | " +
                "OrderId={OrderId} EventId={EventId}",
                @event.OrderId,
                metadata.EventId);
        }   
        catch (JsonException ex)
        {
            sw.Stop();

            activity?.SetTag("worker.deserialized", false);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1,
                new KeyValuePair<string, object?>("operation", "worker.deserialize"),
                new KeyValuePair<string, object?>("queue", Queue));

            // Erro ao converter JSON
            _logger.LogError(ex,
                "Failed to deserialize message - routing to DLQ | " +
                "Queue={Queue} EventId={EventId}",
                Queue, metadata.EventId);

            throw;
        }
        catch (Exception ex)
        {
            sw.Stop();

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1,
                new KeyValuePair<string, object?>("operation", "worker.process"),
                new KeyValuePair<string, object?>("queue", Queue));

            // Erro genérico no processamento da mensagem
            _logger.LogError(ex,
                "Error processing message | Queue={Queue} EventId={EventId}",
                Queue, metadata.EventId);

            throw;
        }
    }
}
