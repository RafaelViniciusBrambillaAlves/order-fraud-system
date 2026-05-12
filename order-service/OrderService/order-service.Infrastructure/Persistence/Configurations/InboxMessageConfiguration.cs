using System;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using order_service.Domain.Entities;

namespace order_service.Infrastructure.Persistence.Configurations;

public sealed class InboxMessageConfiguration : IEntityTypeConfiguration<InboxMessage>
{
    public void Configure(EntityTypeBuilder<InboxMessage> builder)
    {
        builder.ToTable("InboxMessage");

        // PK vem de EntityBase (Guid Id)
        builder.HasKey(x => x.EventId);

        builder.Property(x => x.EventId)
            .IsRequired()
            .HasMaxLength(255);
        
        // Indice unico garante, a nivel de banco, que o mesmo EventId nunca
        // é inserido duas vezes
        builder.HasIndex(x => x.EventId)
            .IsUnique()
            .HasDatabaseName("IX_InboxMessages_EventId");

        builder.Property(x => x.ProcessedAt)
            .IsRequired();
    }
}
