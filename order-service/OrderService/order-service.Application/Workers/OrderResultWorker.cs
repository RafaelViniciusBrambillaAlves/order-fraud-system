using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using order_service.Application.Events;
using order_service.Application.Handlers;
using order_service.Application.Subscribers;
using Microsoft.Extensions.Hosting;

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
        
        _subscriber.Subscribe(Queue, (body, metadata, ct) => DispatchAsync(body, metadata, ct));

        return Task.CompletedTask;
    }

    // Processa a mensagem recebida
    private async Task DispatchAsync(
        ReadOnlyMemory<byte> body, 
        MessageMetadata metadata,
        CancellationToken cancellationToken)
    {
        OrderAnalyzedEvent? @event;

        try
        {   
            // Converte bytes para JSON string
            var json = Encoding.UTF8.GetString(body.Span);

            // Converte JSON para objeto C#
            @event = JsonSerializer.Deserialize<OrderAnalyzedEvent>(json, JsonOptions);

            if (@event is null)
            {   
                _logger.LogWarning(
                   "Received null event after deserialization | Queue={Queue} EventId={EventId} Body={Body}",
                    Queue, metadata.EventId, Encoding.UTF8.GetString(body.Span));
                return;
            }
        }   
        catch (JsonException ex)
        {
            // Erro ao converter JSON
            _logger.LogError(ex, 
                "Failed to deserialize message | Queue={Queue} EventId={EventId}",
                Queue, metadata.EventId);
            return;
        }

        // Cria um escopo de DI
        await using var scope = _scopeFactory.CreateAsyncScope();

        // Obtém o handler responsável pelo evento
        var handler = scope.ServiceProvider.GetRequiredService<OrderAnalyzedEventHandler>();

        // Processa o evento
        await handler.HandleAsync(@event, metadata.EventId, cancellationToken);
    }
}
