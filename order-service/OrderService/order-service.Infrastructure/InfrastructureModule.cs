using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using order_service.Infrastructure.Persistence;
using order_service.Infrastructure.Messaging;
using order_service.Application.Publishers;
using order_service.Infrastructure.Persistence.Repositories; 
using order_service.Domain.Repositories;
using order_service.Application.Subscribers;

namespace order_service.Infrastructure;

public static class InfrastructureModule
{
    public static IServiceCollection AddInfrastructure(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services
            .AddDatabase(configuration)
            .AddMessaging(configuration)
            .AddRepositories();

        return services;    
    }

    private static IServiceCollection AddDatabase(
        this IServiceCollection services, 
        IConfiguration configuration)
    {
        services.AddDbContext<OrderDbContext>(options =>
            options.UseSqlServer(
                configuration.GetConnectionString("DefaultConnection"),
                b =>
                {
                    b.MigrationsAssembly(typeof(OrderDbContext).Assembly.FullName);
                }));

        return services;
    }

    private static IServiceCollection AddMessaging(
        this IServiceCollection services, 
        IConfiguration configuration)
    {
        services.Configure<RabbitMqSettings>(
            configuration.GetSection(RabbitMqSettings.SectionName));

        services.AddSingleton<IEventPublisher, RabbitMqPublisher>();
        services.AddSingleton<IEventSubscriber, RabbitMqSubscriber>();

        services.AddHostedService<OutboxRelayWorker>();

        return services;
    }
   
    private static IServiceCollection AddRepositories(
        this IServiceCollection services)
    {
        services.AddScoped<IOrderRepository, OrderRepository>();
        services.AddScoped<IOutboxRepository, OutboxRepository>();
        services.AddScoped<IInboxRepository, InboxRepository>();

        return services;
    }
}
