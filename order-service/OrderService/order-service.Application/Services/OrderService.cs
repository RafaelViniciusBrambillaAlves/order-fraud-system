using order_service.Application.InputModels;
using order_service.Application.ViewModels;
using order_service.Domain.Entities;
using order_service.Domain.Repositories;
using order_service.Application.Events;
using order_service.Application.Publishers;
using System.Text.Json;
using System.ComponentModel;
using Microsoft.Extensions.Logging;
using order_service.Application.Observability;
using System.Diagnostics;
using OpenTelemetry.Trace;

namespace order_service.Application.Services;

public class OrderService : IOrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly IOutboxRepository  _outboxRepository;
    public readonly ILogger<OrderService> _logger;
    private const string OrderEventsExchange  = "order.events";
    private const string OrderCreatedRoutingKey = "order.created";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public OrderService(
        IOrderRepository orderRepository, 
        IOutboxRepository  outboxRepository,
        ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _outboxRepository = outboxRepository;
        _logger = logger;
    }

    public async Task<OrderViewModel> CreateAsync(
        CreateOrderInputModel input, 
        CancellationToken cancellationToken = default)
    {
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            "order.create",
            ActivityKind.Internal);

        var sw = Stopwatch.StartNew();

        try
        {
            var order = new Order(input.Description, input.Amount);

            activity?.SetTag("order.id", order.Id.ToString());
            activity?.SetTag("order.amount", input.Amount);
            activity?.SetTag("order.amount_range", GetAmountRange(input.Amount));

            var @event = new OrderCreatedEvent(
                EventId: Guid.NewGuid(),
                OrderId: order.Id, 
                Amount:order.Amount,
                CreatedAt: DateTime.UtcNow);    

            var outboxMessage = new OutboxMessage(
                aggregateId: order.Id,
                eventType: nameof(OrderCreatedEvent),
                payload: JsonSerializer.Serialize(@event, JsonOptions),
                exchange: OrderEventsExchange,
                routingKey: OrderCreatedRoutingKey);

            // Sub-span para isolar a latência da persistência
            using (var dbActivity = ApplicationTelemetry.ActivitySource.StartActivity(
                "order.create.db",
                ActivityKind.Internal))
            {   
                dbActivity?.SetTag("db.system", "mssql");
                dbActivity?.SetTag("db.operation", "insert");
                dbActivity?.SetTag("db.sql_server.database", "OrderDb");
                dbActivity?.SetTag("db.rows_affected", 2);

                // Transação atomica: order + outbox ou nada
                await _orderRepository.AddAsync(order, cancellationToken);
                await _outboxRepository.AddAsync(outboxMessage, cancellationToken);
                await _orderRepository.SaveChangesAsync(cancellationToken); 

                dbActivity?.SetStatus(ActivityStatusCode.Ok);
            }

            sw.Stop();

            activity?.SetTag("order.status", order.Status.ToString());
            activity?.SetStatus(ActivityStatusCode.Ok);

            // Métrica de latência de persistência
            ApplicationTelemetry.OrderPersistenceDuration.Record(
                sw.Elapsed.TotalSeconds,
                new KeyValuePair<string, object?>("result", "success"));

            // Contador de pedidos criados
            ApplicationTelemetry.OrdersCreated.Add(1,
                new KeyValuePair<string, object?>("amount.range", GetAmountRange(input.Amount)));

            _logger.LogInformation(
                "Order created successfully | OrderId={OrderId} Amount={Amount}" +
                "AmountRange={AmountRange} DurationMs={DurationMs:F1}",
                order.Id, order.Amount,
                GetAmountRange(input.Amount),
                sw.Elapsed.TotalMilliseconds);    
        
            return OrderViewModel.FromEntity(order);    
        }  
        catch (Exception ex)
        {
            sw.Stop();

            // Marca o span como erro - vermelho no Jaeger
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1, 
                new KeyValuePair<string, object?>("operation", "create"));

            ApplicationTelemetry.OrderPersistenceDuration.Record(
                sw.Elapsed.TotalSeconds,
                new KeyValuePair<string, object?>("result", "error"));


            _logger.LogError(ex, 
                "Failed to create order | Amount={Amount} DurationMs={DurationMs:F1}", 
                input.Amount, sw.Elapsed.TotalMilliseconds);

            throw;
        }
    }

    public async Task<OrderViewModel?> GetByIdAsync(
        Guid id, 
        CancellationToken cancellationToken = default)
    {
        using var activiy = ApplicationTelemetry.ActivitySource.StartActivity(
            "order.get",
            ActivityKind.Internal
        );

        activiy?.SetTag("order.id", id.ToString());
        activiy?.SetTag("db.system", "mssql");
        activiy?.SetTag("db.operation", "select");

        try
        {
            var order = await _orderRepository.GetByIdAsync(id, cancellationToken);

            activiy?.SetTag("order.found", order is not null);

            if (order is not null)
                activiy?.SetTag("order.status", order.Status.ToString());

            activiy?.SetStatus(ActivityStatusCode.Ok);

            return order is null ? null: OrderViewModel.FromEntity(order);
        }
        catch (Exception ex)
        {
            activiy?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activiy?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1, 
                new KeyValuePair<string, object?>("operation", "order.get"));
            
            _logger.LogError(ex, "Failed to get id | OrderId={OrderId}", id);

            throw;
        }
    }

    public async Task<IEnumerable<OrderViewModel>> GetAllAsync(
        CancellationToken cancellationToken = default)
    {
        using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
            "order.list",
            ActivityKind.Internal
        );

        activity?.SetTag("db.system", "mssql");
        activity?.SetTag("db.operation", "select");
    
        try
        {
            var orders = await _orderRepository.GetAllAsync(cancellationToken);
            var result = orders.Select(OrderViewModel.FromEntity).ToList();

            activity?.SetTag("orders.count", result.Count);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return result;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);

            ApplicationTelemetry.OperationErrors.Add(1, 
                new KeyValuePair<string, object?>("operation", "order.list"));

            _logger.LogError(ex, "Failed to get all orders");
            throw;
        }
    }

    private static string GetAmountRange(decimal amount) => amount switch
    {
        < 100 => "0-100",
        < 500 => "100-500",
        < 1000 => "500-1000",
        _ => "1000+"
    };
}
