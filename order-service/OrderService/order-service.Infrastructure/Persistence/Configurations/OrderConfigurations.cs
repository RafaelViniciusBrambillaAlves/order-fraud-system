using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using order_service.Domain.Entities;
using order_service.Domain.Enums;

namespace order_service.Infrastructure.Persistence.Configurations;

public class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> builder)
    {
        builder.ToTable("Orders");

        builder.HasKey(o => o.Id);

        builder.Property(o => o.Description)
            .IsRequired()
            .HasMaxLength(500);

        builder.Property(o => o.Amount)
            .HasColumnType("decimal(18,2)")
            .IsRequired();

        builder.Property(o => o.Status)
            .IsRequired();   

        builder.Property(o => o.CreatedAt) 
            .IsRequired();

        builder.Property(o => o.SagaStartedAt)
            .IsRequired(false);

        builder.Property(o => o.SagaCompletedAt)
            .IsRequired(false);
        
        builder.HasIndex(o => new { o.Status, o.SagaStartedAt })
            .HasFilter($"\"Status\" = {(int)OrderStatus.PENDING_FRAUD_CHECK}")
            .HasDatabaseName("IX_Orders_SagaTimeout");
    }
}
