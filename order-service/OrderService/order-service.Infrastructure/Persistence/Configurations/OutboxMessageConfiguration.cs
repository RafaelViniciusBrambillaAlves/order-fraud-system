using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using order_service.Domain.Entities;
namespace order_service.Infrastructure.Persistence.Configurations;

public sealed class OutboxMessageConfiguration : IEntityTypeConfiguration<OutboxMessage>
{
    public void Configure(EntityTypeBuilder<OutboxMessage> builder)
    {
        builder.ToTable("OutboxMessages");

        builder.HasKey(o => o.Id);

        builder.Property(o => o.EventType)
            .IsRequired()
            .HasMaxLength(200);

        builder.Property(o => o.Payload)
            .IsRequired()
            .HasColumnType("nvarchar(max)");

        builder.Property(o => o.Exchange)
            .IsRequired()
            .HasMaxLength(200);
        
        builder.Property(o => o.RoutingKey)
            .IsRequired()
            .HasMaxLength(200);

        builder.Property(o => o.Status)
            .IsRequired();

        builder.Property(o => o.LastError)
            .HasMaxLength(2000);

        builder.HasIndex(o => new { o.Status, o.CreatedAt })
            .HasFilter("[Status] = 0")
            .HasDatabaseName("IX_OutboxMessages_Pending");
    }
}
