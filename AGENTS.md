# AGENTS.md — Order Fraud System

> Instruções carregadas pelo Codex antes de qualquer tarefa neste repositório.
> Leia tudo antes de propor ou aplicar qualquer mudança.

---

## Visão geral do sistema

Este repositório implementa um sistema de pedidos com análise antifraude baseado em microsserviços:

| Serviço         | Tecnologia          | Banco de dados | Mensageria          |
|-----------------|---------------------|----------------|---------------------|
| `order-service` | .NET 8 / C#         | SQL Server     | RabbitMQ (producer) |
| `fraud-service` | Python 3.11 FastAPI | MongoDB        | RabbitMQ (consumer) |

### Fluxo principal (Saga)

```text
POST /api/orders
  → order-service persiste Order + OutboxMessage (transação atômica)
  → OutboxRelayWorker publica OrderCreatedEvent no RabbitMQ
  → fraud-service consome → analisa → publica OrderAnalyzedEvent
  → order-service consome → atualiza status do pedido
```

### Padrões críticos que DEVEM ser respeitados

1. **Outbox Pattern** — nunca publique direto no RabbitMQ dentro de um handler HTTP.
   Persista `OutboxMessage` junto com o agregado na mesma transação.
2. **Inbox Pattern** — antes de processar qualquer evento consumido, verifique
   se o `EventId` já existe na tabela/coleção de inbox. Se existir, ignore silenciosamente.
3. **Saga com timeout** — pedidos ficam em `PENDING_FRAUD_CHECK`. O `SagaTimeoutWorker`
   expira pedidos que ultrapassam o tempo configurado em `SagaTimeout:FraudAnalysisTimeout`.
4. **Dead Letter Queue (DLQ)** — mensagens rejeitadas ou expiradas vão para DLQs.
   O `DlqWorker` (C#) e o `DlqConsumer` (Python) apenas logam e emitem métricas.
   Nunca reprocesse na DLQ sem idempotência garantida.

---

## Antes de fazer qualquer alteração

1. **Leia os arquivos relevantes primeiro** — não assuma o conteúdo de arquivos
   que não foram exibidos explicitamente nesta sessão.
2. **Nunca altere migrações existentes** em `order-service.Infrastructure/Migrations/`.
   Crie uma nova migração com `dotnet ef migrations add <NomeMigração>`.
3. **Não remova propriedades de eventos** (`OrderCreatedEvent`, `OrderAnalyzedEvent`).
   Esses são contratos entre serviços. Apenas adicione propriedades novas.
4. **Pergunte antes de adicionar dependências** de produção (NuGet packages, pip packages).

---

## Comandos de verificação obrigatórios

Execute estes comandos após qualquer alteração e certifique-se de que passam antes de propor o PR:

### order-service (.NET)

```bash
# Compilar
dotnet build order-service/OrderService/OrderService.sln

# Testes (quando existirem)
dotnet test order-service/OrderService/OrderService.sln

# Verificar se há warnings novos de nullable
dotnet build order-service/OrderService/OrderService.sln -warnaserror:nullable
```

### fraud-service (Python)

```bash
# Instalar dependências
pip install -r fraud-service/requirements.txt

# Verificar tipos (se mypy estiver disponível)
mypy fraud-service/app --ignore-missing-imports

# Testes (quando existirem)
pytest fraud-service/tests/ -v
```

### Infraestrutura

```bash
# Validar docker-compose
docker compose config --quiet

# Checar se o RabbitMQ definitions.json é JSON válido
python3 -c "import json; json.load(open('rabbitmq/definitions.json'))"
```

---

## Convenções de código

### C# (order-service)

- Arquitetura em camadas: `Domain` → `Application` → `Infrastructure` → `API`.
  Dependências só fluem para dentro (Domain não referencia Infrastructure).
- Entidades de domínio têm construtores com parâmetros. EF Core usa construtor
  privado sem parâmetros para rehidratação.
- Observabilidade: use `ApplicationTelemetry.ActivitySource.StartActivity()`
  para spans customizados. Siga o padrão já estabelecido em `OrderService.cs`.
- Handlers são `sealed`. Workers são `BackgroundService`.
- Prefira `IServiceScopeFactory` em workers de longa duração (nunca injete
  serviços `Scoped` diretamente em `Singleton`).

### Python (fraud-service)

- Entidades herdam de `EntityBase` (Pydantic `BaseModel`).
- Repositórios implementam interfaces abstratas (`IOrderRepository`, etc.).
- Handlers orquestram casos de uso; não colocam lógica de negócio diretamente.
- Use `tracer.start_as_current_span(...)` com `SpanKind` explícito para observabilidade.
- Settings via `pydantic_settings.BaseSettings`. Nunca hardcode credenciais.
- Sessões MongoDB: passe `session` para operações dentro de transações.

---

## Estrutura de diretórios relevante

```text
.
├── AGENTS.md                          ← este arquivo
├── docker-compose.yml
├── rabbitmq/
│   ├── definitions.json               ← topologia do RabbitMQ (exchanges, queues, bindings)
│   └── rabbitmq.conf
├── observability/
│   ├── otel-collector.yml
│   ├── prometheus.yml
│   └── grafana/
├── order-service/
│   ├── Dockerfile
│   ├── .env.example
│   └── OrderService/
│       ├── order-service.API/         ← controllers, Program.cs
│       ├── order-service.Application/ ← services, handlers, workers, events
│       ├── order-service.Domain/      ← entities, enums, repository interfaces
│       └── order-service.Infrastructure/ ← EF Core, RabbitMQ, migrations
└── fraud-service/
    ├── Dockerfile
    ├── .env.example
    ├── requirements.txt
    └── app/
        ├── api/routes/
        ├── application/handlers/
        ├── core/                      ← settings, startup, dependencies
        ├── domain/                    ← entities, enums, repository interfaces
        ├── infrastructure/database/   ← repositórios MongoDB
        ├── messaging/                 ← consumers, publishers, workers
        ├── observability/             ← telemetry, metrics
        └── schemas/                   ← eventos (contratos externos)
```

---

## Topologia do RabbitMQ

| Exchange              | Tipo   | Routing Key          | Destino                  |
|-----------------------|--------|----------------------|--------------------------|
| `order.events`        | direct | `order.created`      | `fraud.analysis.queue`   |
| `fraud.events`        | direct | `order.approved`     | `order.result.queue`     |
| `fraud.events`        | direct | `order.rejected`     | `order.result.queue`     |
| `dead.letter.exchange`| direct | `fraud.analysis.dlq` | `fraud.analysis.dlq`     |
| `dead.letter.exchange`| direct | `order.result.dlq`   | `order.result.dlq`       |

---

## Observabilidade

- **Traces**: OTLP → otel-collector → Jaeger (porta 16686)
- **Métricas**: OTLP → otel-collector → Prometheus (porta 9090) → Grafana (porta 3001)
- Ao criar novos spans, siga o padrão de nomenclatura: `<serviço>.<domínio>.<ação>`
  Exemplos: `order.create`, `fraud.analyze_order`, `outbox.relay.publish`
- Ao criar novas métricas, registre-as em `ApplicationTelemetry.cs` (C#)
  ou `fraud_metrics.py` (Python). Nunca crie métricas inline em handlers.

---

## O que NÃO fazer

- ❌ Não use `Thread.Sleep` ou `time.sleep` em loops de produção — use `await Task.Delay` / `asyncio.sleep`.
- ❌ Não exponha a connection string em logs
- ❌ Não faça `BasicPublish` sem `WaitForConfirms` no publisher C#.
- ❌ Não use `autoAck: true` em consumers — sempre use ACK/NACK explícito.
- ❌ Não modifique `rabbitmq/definitions.json` sem ajustar os consumers correspondentes.
- ❌ Não acesse `request.app.state` fora de rotas FastAPI — use injeção de dependência.

---

## Skills disponíveis neste projeto

Skills são workflows especializados que o Codex pode ativar para tarefas específicas:

| Skill                     | Ativação sugerida                                               |
|---------------------------|-----------------------------------------------------------------|
| `adicionar-feature`       | "Implemente X no order-service / fraud-service"                 |
| `escrever-testes`         | "Escreva testes para Y"                                         |
| `revisar-codigo`          | "Revise este arquivo / PR"                                      |
| `criar-migracao-ef`       | "Crie uma migration EF Core para Z"                             |
| `adicionar-metrica-otel`  | "Adicione uma métrica de observabilidade para W"                |
| `security-review`         | "Revise o código X em busca de vulnerabilidade de segurança"    |

As skills ficam em `.agents/skills/` dentro deste repositório.
