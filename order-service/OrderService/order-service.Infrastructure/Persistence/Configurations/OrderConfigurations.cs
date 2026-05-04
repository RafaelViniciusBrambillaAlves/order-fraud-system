using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using order_service.Domain.Entities;


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
    }
}
