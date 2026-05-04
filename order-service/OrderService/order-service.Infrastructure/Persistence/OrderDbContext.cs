using Microsoft.EntityFrameworkCore;
using order_service.Domain.Entities;

namespace order_service.Infrastructure.Persistence;

public class OrderDbContext : DbContext 
{
    public OrderDbContext(DbContextOptions<OrderDbContext> options)
        : base(options)
    {
    }

    public DbSet<Order> Orders { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(OrderDbContext).Assembly);
        base.OnModelCreating(modelBuilder);
    } 
}
