---
name: revisar-codigo
description: >
  Use esta skill para revisar código, PRs ou arquivos específicos em busca de bugs,
  problemas de design, violações de padrão e oportunidades de melhoria.
  Ativa quando o usuário pede "revise", "code review", "analise este arquivo",
  "o que está errado neste código", "tem algum problema aqui".
---

# Skill: Revisar Código

Realize a revisão em camadas, da mais crítica para a menos crítica.

---

## Camada 1 — Corretude e segurança (bugs que podem ir para produção)

Verifique:

### Padrões transacionais
- [ ] Operações de escrita em banco sempre têm `SaveChangesAsync` após todas as operações
      da transação. Não há `SaveChanges` parcial que possa quebrar consistência.
- [ ] OutboxMessage é sempre persistida **junto** com o agregado, nunca em separado.
- [ ] Consumer verifica idempotência (inbox) antes de qualquer lógica de negócio.

### Gestão de recursos
- [ ] Connections e channels RabbitMQ são disposed corretamente.
- [ ] `using` ou `await using` em recursos IDisposable / IAsyncDisposable.
- [ ] Workers de longa duração não injetam serviços `Scoped` diretamente —
      usam `IServiceScopeFactory`.

### Tratamento de erros
- [ ] Exceções em consumers resultam em NACK (não ACK silencioso).
- [ ] Spans de telemetria chamam `SetStatus(Error)` e `RecordException` em `catch`.
- [ ] Não há `catch (Exception)` vazio ou que engole o erro sem logar.

### Contratos de eventos
- [ ] Nenhuma propriedade foi removida ou renomeada em eventos existentes.
- [ ] Novos campos de evento têm `[JsonPropertyName]` / `Field(alias=...)` corretos.

---

## Camada 2 — Design e arquitetura

### C# (order-service)
- [ ] Respeita a hierarquia de dependências: Domain não referencia Application nem Infrastructure.
- [ ] Lógica de negócio fica em entidades de domínio ou handlers, não em controllers.
- [ ] Controllers são finos — apenas validação, delegação e mapeamento de resultado.
- [ ] `sealed` em handlers e records onde aplicável.
- [ ] Métodos públicos em entidades de domínio lançam exceção para estados inválidos
      (ex: `UpdateStatus` em pedido já finalizado).

### Python (fraud-service)
- [ ] Handlers não contêm lógica de negócio — apenas orquestram use cases.
- [ ] Use cases são funções puras ou classes sem estado quando possível.
- [ ] Repositórios implementam a interface abstraia (ABC) — não acoplam ao MongoDB diretamente nos handlers.
- [ ] `model_config = {"frozen": False}` apenas quando necessário (entidades mutáveis).

---

## Camada 3 — Observabilidade

- [ ] Novos fluxos relevantes têm spans com nome no padrão `dominio.operacao`.
- [ ] Tags/atributos de span seguem o padrão `snake_case` e são consistentes
      com os existentes (ex: `order.id`, `fraud.status`).
- [ ] Novas métricas estão registradas nos arquivos centrais
      (`ApplicationTelemetry.cs` ou `fraud_metrics.py`), não inline.
- [ ] Não há dados sensíveis (senhas, tokens, PII) em tags de span ou logs.

---

## Camada 4 — Qualidade e manutenibilidade

- [ ] Não há duplicação de lógica que deveria estar centralizada.
- [ ] Nomes de variáveis, métodos e classes são claros e consistentes com o restante do código.
- [ ] Comentários explicam o "por quê", não o "o quê" (o código já faz isso).
- [ ] Não há código comentado ou debugging temporário (`Console.WriteLine` de debug,
      `print()` de debug, breakpoints).
- [ ] Strings mágicas (exchange names, routing keys, queue names) são constantes ou configuração,
      não literais espalhados pelo código.

---

## Formato do relatório de revisão

Para cada problema encontrado, reporte:

```
### [CRÍTICO | IMPORTANTE | SUGESTÃO] — <título curto>

**Arquivo**: `caminho/para/arquivo.cs` linha X
**Problema**: Descrição clara do que está errado e por quê é um problema.
**Sugestão**: Como corrigir, com exemplo de código quando relevante.
```

Ao final, inclua um resumo:
- Quantos problemas críticos (impedem merge)
- Quantos importantes (devem ser corrigidos antes do merge)
- Quantas sugestões (podem ser endereçadas em follow-up)
- Uma avaliação geral em 1-2 frases