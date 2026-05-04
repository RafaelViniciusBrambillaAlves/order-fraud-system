using System;

namespace order_service.Domain.Entities;

public abstract class EntityBase
{
    public EntityBase()
    {
        Id = Guid.NewGuid();
    }

    public Guid Id { get; private set; }
}
