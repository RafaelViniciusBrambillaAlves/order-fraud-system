using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace order_service.Infrastructure.Persistence;

public static class DbContextExtensions
{
    public static async Task ApplyMigrationsAsync(this IServiceProvider serviceProvider)
    {
        using var scope = serviceProvider.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<OrderDbContext>();

        await dbContext.Database.MigrateAsync();
    }
}
