---
name: criar-migracao-ef
description: >
  Use esta skill para criar ou ajustar migrações EF Core no order-service.
  Ativa quando o usuário pede para "criar migration", "adicionar migration EF Core",
  "adicionar coluna no banco", "alterar tabela", "novo índice no SQL Server".
  Apenas para o order-service (.NET). O fraud-service usa MongoDB sem migrations.
---

# Skill: Criar Migration EF Core

## Regra principal

**NUNCA edite arquivos de migration já existentes** em
`order-service/OrderService/order-service.Infrastructure/Migrations/`.
Cada migration representa um estado histórico do banco. Alterá-las corromperia
o histórico de deploy.

---

## Passo 1 — Fazer a mudança no modelo de domínio

Altere primeiro a entidade em `order-service.Domain/Entities/`:

```csharp
// Exemplo: adicionar campo CustomerEmail em Order
public class Order : EntityBase
{
    // ...campos existentes...

    public string? CustomerEmail { get; private set; }  // nova propriedade

    public Order(string description, decimal amount, string? customerEmail = null)
    {
        // ...
        CustomerEmail = customerEmail;
    }
}
```

---

## Passo 2 — Configurar no EF (Fluent API)

Adicione ou edite a configuração em
`order-service.Infrastructure/Persistence/Configurations/`:

```csharp
// OrderConfiguration.cs
builder.Property(o => o.CustomerEmail)
    .HasMaxLength(320)
    .IsRequired(false);

// Se precisar de índice:
builder.HasIndex(o => o.CustomerEmail)
    .HasDatabaseName("IX_Orders_CustomerEmail");
```

---

## Passo 3 — Verificar se compila antes de gerar a migration

```bash
dotnet build order-service/OrderService/OrderService.sln
```

Não gere a migration se houver erros de compilação.

---

## Passo 4 — Gerar a migration

```bash
cd order-service/OrderService

dotnet ef migrations add <NomeDaMigration> \
  --project order-service.Infrastructure \
  --startup-project order-service.API \
  --output-dir Migrations
```

Convenção de nomenclatura para `<NomeDaMigration>`:
- `Add<Entidade><Campo>` → ex: `AddOrderCustomerEmail`
- `Add<Entidade>Table` → ex: `AddAuditLogTable`
- `Add<Entidade><Campo>Index` → ex: `AddOrderCustomerEmailIndex`
- `Remove<Entidade><Campo>` → ex: `RemoveOrderLegacyField`

---

## Passo 5 — Revisar o arquivo gerado

Abra o arquivo `.cs` gerado em `Migrations/` e verifique:

- [ ] O método `Up()` faz o que você esperava (colunas, índices corretos)
- [ ] O método `Down()` desfaz corretamente (para rollback)
- [ ] O tipo SQL está correto para o campo (ex: `nvarchar(320)`, `decimal(18,2)`)
- [ ] Índices têm `HasFilter` quando são índices parciais (ex: status específico)

### Exemplo de índice parcial correto:
```csharp
migrationBuilder.CreateIndex(
    name: "IX_Orders_SagaTimeout",
    table: "Orders",
    columns: new[] { "Status", "SagaStartedAt" },
    filter: "\"Status\" = 1");   // ← só indexa pedidos PENDING
```

---

## Passo 6 — Verificar o ModelSnapshot

O arquivo `OrderDbContextModelSnapshot.cs` deve ter sido atualizado automaticamente.
Confirme que a nova propriedade/índice aparece lá.

---

## Passo 7 — Compilar novamente

```bash
dotnet build order-service/OrderService/OrderService.sln
```

---

## Observações importantes

- A migration é aplicada automaticamente no startup via `ApplyMigrationsAsync()`
  em `Program.cs`. Não é necessário `dotnet ef database update` em produção.
- Para SQL Server com `nvarchar(max)`, use `HasColumnType("nvarchar(max)")` na config,
  não `HasMaxLength`.
- Se a migration alterar uma tabela existente com dados, avalie se precisa de um
  valor default para colunas `NOT NULL`. EF Core gera automaticamente, mas confirme.
- Após criar a migration, verifique se o `OrderDbContextModelSnapshot.cs` está
  consistente — inconsistências causam erros na próxima migration.