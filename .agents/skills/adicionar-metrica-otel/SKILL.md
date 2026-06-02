---
name: adicionar-metrica-otel
description: >
  Use esta skill para adicionar métricas, spans ou atributos de observabilidade
  OpenTelemetry ao sistema. Ativa quando o usuário pede para "adicionar métrica",
  "instrumentar", "adicionar observabilidade", "criar span", "adicionar tracing",
  "medir latência de", "contar ocorrências de", "criar dashboard Grafana para".
---

# Skill: Adicionar Métrica / Span OpenTelemetry

## Arquitetura de observabilidade do projeto

```
order-service (.NET)   ──┐
                         ├──► OTLP gRPC ──► otel-collector ──► Jaeger  (traces)
fraud-service (Python) ──┘                                  └──► Prometheus ──► Grafana (métricas)
```

Porta OTLP: `4317` (gRPC). Configurado em `appsettings.json` e `.env`.

---

## Adicionar uma MÉTRICA

### C# — Registrar no arquivo central

**Arquivo**: `order-service.Application/Observability/ApplicationTelemetry.cs`

```csharp
// CONTADOR (eventos que acontecem)
public static readonly Counter<long> MeuContador =
    Meter.CreateCounter<long>(
        name: "orders.meu_evento.total",
        unit: "{eventos}",
        description: "Descrição clara do que este contador mede"
    );

// HISTOGRAMA (latência, tamanho, duração)
public static readonly Histogram<double> MinhaLatencia =
    Meter.CreateHistogram<double>(
        name: "orders.minha_operacao.duration.seconds",
        unit: "s",
        description: "Duração da operação X em segundos"
    );

// GAUGE OBSERVÁVEL (valor atual de algo — ex: pedidos pendentes)
public static readonly ObservableGauge<int> MeuGauge;
// No static constructor:
MeuGauge = Meter.CreateObservableGauge(
    name: "orders.meu_recurso.current",
    observeValue: () => new Measurement<int>(ObterValorAtual()),
    unit: "{itens}",
    description: "Quantidade atual de X"
);
```

**Usar no código:**
```csharp
// Contador com tag dimensional
ApplicationTelemetry.MeuContador.Add(1,
    new KeyValuePair<string, object?>("dimensao", valor));

// Histograma
var sw = Stopwatch.StartNew();
// ... operação ...
sw.Stop();
ApplicationTelemetry.MinhaLatencia.Record(sw.Elapsed.TotalSeconds,
    new KeyValuePair<string, object?>("resultado", "sucesso"));
```

### Python — Registrar no arquivo central

**Arquivo**: `fraud-service/app/observability/fraud_metrics.py`

```python
# CONTADOR
meu_contador = _meter.create_counter(
    name="fraud.meu_evento.total",
    unit="{eventos}",
    description="Descrição clara do que este contador mede"
)

# HISTOGRAMA
minha_latencia = _meter.create_histogram(
    name="fraud.minha_operacao.duration.seconds",
    unit="s",
    description="Duração da operação X em segundos"
)
```

**Usar no código:**
```python
import time
from app.observability import fraud_metrics

# Contador
fraud_metrics.meu_contador.add(1, {"dimensao": valor})

# Histograma
start = time.perf_counter()
# ... operação ...
fraud_metrics.minha_latencia.record(
    time.perf_counter() - start,
    {"resultado": "sucesso"}
)
```

---

## Adicionar um SPAN customizado

### C# — Span dentro de um método

```csharp
using var activity = ApplicationTelemetry.ActivitySource.StartActivity(
    "dominio.sub_operacao",          // nome: dominio.operacao
    ActivityKind.Internal);           // Internal | Producer | Consumer | Client | Server

// Tags semânticas (snake_case)
activity?.SetTag("order.id", order.Id.ToString());
activity?.SetTag("order.amount", order.Amount);

try
{
    // ... lógica ...
    activity?.SetStatus(ActivityStatusCode.Ok);
}
catch (Exception ex)
{
    activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
    activity?.RecordException(ex);
    throw;
}
```

### Python — Span dentro de um método

```python
with tracer.start_as_current_span(
    "dominio.sub_operacao",
    kind=SpanKind.INTERNAL     # INTERNAL | PRODUCER | CONSUMER | CLIENT | SERVER
) as span:
    span.set_attribute("order.id", str(order_id))
    span.set_attribute("order.amount", float(amount))

    try:
        # ... lógica ...
        span.set_status(Status(StatusCode.OK))
    except Exception as exc:
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        raise
```

---

## Convenções de nomenclatura

### Nomes de métricas
- Formato: `<serviço>.<domínio>.<ação>.<unidade>`
- Exemplos: `orders.created.total`, `fraud.analysis.duration.seconds`
- Use `snake_case`, sem hífens.

### Nomes de spans
- Formato: `<domínio>.<ação>` (sem prefixo de serviço — o serviço já está no resource)
- Exemplos: `order.create`, `fraud.analyze_order`, `outbox.relay.publish`
- Para messaging: `rabbitmq.publish <exchange>/<routing_key>` ou `rabbitmq.consume <queue>`

### Tags/Atributos semânticos (seguir OpenTelemetry semantic conventions)
```
order.id          → ID do pedido (string UUID)
order.amount      → Valor do pedido (float)
fraud.status      → "approved" | "rejected"
messaging.system  → "rabbitmq"
db.system         → "mssql" | "mongodb"
db.operation      → "insert" | "select" | "update"
```

---

## Criar um painel no Grafana

Após adicionar a métrica, o Prometheus coleta automaticamente via otel-collector.
Para criar um novo painel ou editar um painel existente, de acordo com o nome da métrica:

1. Acesse Grafana em `http://localhost:3001`
2. Vá em Dashboards → New Panel
3. Use a query PromQL baseada no nome da métrica com prefixo `otel_`:
   - Contador: `rate(otel_orders_meu_evento_total[5m])`
   - Histograma P95: `histogram_quantile(0.95, rate(otel_orders_minha_operacao_duration_seconds_bucket[5m]))`
4. Salve o dashboard em `observability/grafana/dashboards/<nome>.json`

### Exemplos de queries por tipo:

```promql
# Taxa de eventos por segundo (contador)
rate(otel_orders_meu_evento_total[5m])

# P95 de latência (histograma)
histogram_quantile(0.95,
  sum by (le) (
    rate(otel_orders_minha_operacao_duration_seconds_bucket[5m])
  )
)

# Taxa de erros
rate(otel_orders_operation_errors_total{operation="minha_op"}[5m])
  /
rate(otel_orders_meu_evento_total[5m])
```

---

## Checklist antes de considerar concluído

- [ ] Métrica registrada no arquivo central (não inline)
- [ ] Nome segue a convenção `snake_case` com prefixo do serviço
- [ ] Tags dimensionais são de baixa cardinalidade (não use UUIDs como tag!)
- [ ] Span tem `SetStatus` no caminho feliz e no `catch`
- [ ] Span tem `RecordException` em caso de erro
- [ ] Nenhum dado sensível (PII, credencial) em tags ou atributos