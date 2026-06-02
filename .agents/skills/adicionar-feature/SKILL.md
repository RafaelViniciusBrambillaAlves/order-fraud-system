---
name: adicionar-feature
description: >
  Use esta skill para implementar uma nova funcionalidade em qualquer parte do sistema
  order-fraud. Ativa quando o usuário pede para "implementar", "adicionar", "criar"
  algo no order-service (.NET/C#) ou no fraud-service (Python/FastAPI).
  Não ativar para tarefas de revisão, testes isolados ou migrações de banco.
---

# Skill: Adicionar Feature

Siga este roteiro em ordem. Não pule etapas.

## 1. Entender o contexto antes de escrever qualquer código

- Leia os arquivos existentes relacionados à feature. Nunca assuma o conteúdo.
- Identifique em qual camada a mudança pertence:
  - **Domain**: nova entidade, enum, interface de repositório
  - **Application**: novo handler, service, worker, evento
  - **Infrastructure**: novo repositório, configuração EF, integração RabbitMQ
  - **API**: novo endpoint, input model, view model
- Para o fraud-service, siga a mesma separação: `domain/`, `application/`, `infrastructure/`, `api/`.

## 2. Verificar contratos existentes

- Se a feature envolve mensagens RabbitMQ, verifique `rabbitmq/definitions.json`.
  Novos exchanges ou filas devem ser adicionados lá antes de codificar os consumers.
- Se envolve um novo evento entre serviços, adicione em:
  - C#: `order-service.Application/Events/`
  - Python: `fraud-service/app/schemas/`
- **Regra de ouro**: nunca remova ou renomeie campos de eventos existentes.

## 3. Implementar seguindo os padrões estabelecidos

### Se for no order-service (.NET):

```
Checklist:
[ ] Entidade de domínio com construtor com parâmetros + construtor privado sem params para EF
[ ] Interface de repositório em Domain/Repositories/
[ ] Implementação do repositório em Infrastructure/Persistence/Repositories/
[ ] Configuração EF em Infrastructure/Persistence/Configurations/ (IEntityTypeConfiguration<T>)
[ ] Handler registrado em ApplicationModule.cs
[ ] Repositório registrado em InfrastructureModule.cs
[ ] Se usar OutboxMessage: persistir Order + OutboxMessage na mesma transação
[ ] Se consumir evento: verificar InboxRepository.ExistsAsync() antes de processar
```

### Se for no fraud-service (Python):

```
Checklist:
[ ] Entidade herda de EntityBase (Pydantic BaseModel)
[ ] Interface de repositório em domain/repositories/ (ABC)
[ ] Implementação em infrastructure/database/repositories/
[ ] Handler em application/handlers/ — apenas orquestração, sem lógica de negócio
[ ] Lógica de negócio em application/use_cases/
[ ] Novo consumer registrado em core/startup.py dentro do lifespan
[ ] Se usar OutboxMessage: persistir order + outbox na mesma sessão MongoDB
[ ] Se consumir evento: verificar inbox_repository.exists_async() antes de processar
```

## 4. Adicionar observabilidade

Toda nova operação relevante deve ter:

### C# — span customizado:
```csharp
using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
    "dominio.operacao",
    ActivityKind.Internal);

activity?.SetTag("chave", valor);
// ... lógica ...
activity?.SetStatus(ActivityStatusCode.Ok);
```

### Python — span customizado:
```python
with tracer.start_as_current_span(
    "dominio.operacao",
    kind=SpanKind.INTERNAL
) as span:
    span.set_attribute("chave", valor)
    # ... lógica ...
    span.set_status(Status(StatusCode.OK))
```

Se a feature gera métricas de negócio (contagem, latência), registre em
`ApplicationTelemetry.cs` (C#) ou `fraud_metrics.py` (Python).

## 5. Verificar e compilar

Após implementar, execute:

```bash
# order-service
dotnet build order-service/OrderService/OrderService.sln

# fraud-service
cd fraud-service && python -c "from app.main import app; print('OK')"
```

Corrija todos os erros de compilação antes de apresentar o resultado.

## 6. Resumir o que foi feito

Ao finalizar, liste:
- Arquivos criados (com caminho completo)
- Arquivos modificados (com caminho completo + o que mudou)
- Arquivos que podem precisar de atenção futura (ex: migrations, config de infra)