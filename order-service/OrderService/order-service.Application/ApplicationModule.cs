using Microsoft.Extensions.DependencyInjection;
using order_service.Application.Services;

namespace order_service.Application;

public static class ApplicationModule
{
    public static IServiceCollection AddAplication(this IServiceCollection services)
    {
        services.AddScoped<IOrderService, OrderService>();
     
        return services;
    }
}
