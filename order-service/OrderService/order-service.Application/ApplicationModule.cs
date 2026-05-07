using Microsoft.Extensions.DependencyInjection;
using order_service.Application.Events;
using order_service.Application.Handlers;
using order_service.Application.Services;
using order_service.Application.Workers;

namespace order_service.Application;

public static class ApplicationModule
{
    public static IServiceCollection AddAplication(this IServiceCollection services)
    {
        services.AddScoped<IOrderService, OrderService>();

        services.AddScoped<OrderAnalyzedEventHandler>();

        services.AddHostedService<OrderResultWorker>();
     
        return services;
    }
}
