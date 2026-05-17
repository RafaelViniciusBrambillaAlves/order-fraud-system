using Microsoft.Extensions.DependencyInjection;
using order_service.Application.Events;
using order_service.Application.Handlers;
using order_service.Application.Services;
using order_service.Application.Workers;
using Microsoft.Extensions.Configuration;
using order_service.Application.Settings;

namespace order_service.Application;

public static class ApplicationModule
{
    public static IServiceCollection AddApplication(
        this IServiceCollection services,
        IConfiguration configuration)
    {   
        // Settings
        services.Configure<SagaTimeoutSettings>(configuration.GetSection(SagaTimeoutSettings.Section));

        // Services
        services.AddScoped<IOrderService, OrderService>();

        // Handlers 
        services.AddScoped<OrderAnalyzedEventHandler>();

        // Workers
        services.AddHostedService<OrderResultWorker>();
        services.AddHostedService<SagaTimeoutWorker>();

        return services;
    }
}
