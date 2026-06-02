---
name: security-review
description: >
  Use esta skill para revisar código, configurações, infraestrutura e
  observabilidade em busca de vulnerabilidades de segurança.
  Ativa quando o usuário pede para "revisar segurança",
  "security review", "analisar vulnerabilidades",
  "encontrar riscos", "hardening", "secure code review",
  "tem algo inseguro aqui?" ou antes de merge em produção.
---

# Skill: Security Review

Objetivo:
Identificar riscos de segurança antes que cheguem à produção.

A revisão deve seguir as camadas abaixo, da mais crítica para a menos crítica.

Nunca assumir que um sistema é seguro apenas porque funciona.

---

# Camada 1 — Segredos e Credenciais (CRÍTICO)

Verificar:

## Arquivos de configuração

- [ ] Nenhuma senha está hardcoded.
- [ ] Nenhuma connection string contém credenciais reais.
- [ ] Nenhuma chave JWT está commitada.
- [ ] Nenhuma API Key está commitada.
- [ ] Nenhum token está em appsettings.json.
- [ ] Nenhum token está em settings.py.
- [ ] Nenhum segredo está em docker-compose.yml.

Aceitável:

```json
{
  "ConnectionStrings": {
    "SqlServer": "${SQLSERVER_CONNECTION_STRING}"
  }
}
```

Não aceitável:

```json
{
  "ConnectionStrings": {
    "SqlServer": "Server=db;User Id=sa;Password=Senha123!"
  }
}
```

---

## Variáveis de ambiente

Verificar:

- [ ] Existe `.env.example`.
- [ ] Não existe `.env` commitado.
- [ ] `.gitignore` ignora `.env`.
- [ ] Credenciais são carregadas via ambiente.

---

# Camada 2 — APIs (.NET e FastAPI)

Verificar:

## Entrada de dados

- [ ] Inputs possuem validação.
- [ ] Não existe trust em dados vindos do cliente.
- [ ] IDs recebidos são validados.
- [ ] Valores monetários são validados.
- [ ] Enum parsing é seguro.

### C#

Verificar:

```csharp
[Required]
[StringLength(200)]
```

ou FluentValidation.

### Python

Verificar:

```python
class CreateOrderRequest(BaseModel):
    description: str = Field(max_length=200)
    amount: float = Field(gt=0)
```

---

## Mass Assignment

Verificar:

- [ ] Entidades não são populadas diretamente do request.

Não aceitável:

```csharp
var order = request;
```

Aceitável:

```csharp
var order = new Order(
    request.Description,
    request.Amount
);
```

---

## Exposição de erros

Verificar:

- [ ] Stacktrace não retorna ao cliente.
- [ ] Exceptions não revelam infraestrutura.

Não aceitável:

```json
{
  "error": "MongoConnectionException ..."
}
```

Aceitável:

```json
{
  "error": "Unexpected error."
}
```

---

# Camada 3 — Banco de Dados

## SQL Injection

Verificar:

- [ ] Queries parametrizadas.
- [ ] Nenhum SQL concatenado.

Não aceitável:

```csharp
$"SELECT * FROM Orders WHERE Id = {id}"
```

Aceitável:

EF Core LINQ

```csharp
db.Orders.FirstOrDefaultAsync(x => x.Id == id);
```

---

## Mongo Injection

Verificar:

- [ ] Queries usam filtros tipados.
- [ ] Nenhum JSON montado por string.

Não aceitável:

```python
db.orders.find(json.loads(user_input))
```

---

## Dados sensíveis

Verificar:

- [ ] CPF não é logado.
- [ ] Email não é logado.
- [ ] Cartão não é logado.
- [ ] Telefone não é logado.

---

# Camada 4 — RabbitMQ

Verificar:

## Producers

- [ ] Publisher Confirms habilitado.
- [ ] Eventos não carregam segredos.
- [ ] Payload mínimo necessário.

---

## Consumers

- [ ] autoAck = false
- [ ] ACK explícito
- [ ] NACK explícito
- [ ] Idempotência via Inbox

---

## Filas

Verificar:

- [ ] DLQ configurada.
- [ ] TTL configurado quando aplicável.
- [ ] Durable=true.

---

# Camada 5 — Autenticação e Autorização

Verificar:

## JWT

- [ ] Chave forte.
- [ ] Expiração configurada.
- [ ] Algoritmo explícito.
- [ ] Audience configurado.
- [ ] Issuer configurado.

---

## Roles

Verificar:

- [ ] Endpoints protegidos.
- [ ] Não existe endpoint administrativo aberto.

### C#

```csharp
[Authorize]
```

ou

```csharp
[Authorize(Roles="Admin")]
```

### FastAPI

Verificar dependências de autenticação.

---

# Camada 6 — Docker

Verificar:

## Containers

- [ ] Não executam como root.
- [ ] Possuem usuário dedicado.
- [ ] Imagens atualizadas.

Não aceitável:

```dockerfile
USER root
```

Aceitável:

```dockerfile
RUN adduser appuser
USER appuser
```

---

## Volumes

Verificar:

- [ ] Apenas diretórios necessários são montados.
- [ ] Não existe bind mount sensível.

---

## Portas

Verificar:

- [ ] Apenas portas necessárias expostas.
- [ ] Mongo não exposto externamente.
- [ ] SQL Server não exposto externamente.
- [ ] RabbitMQ management protegido.

---

# Camada 7 — Observabilidade

Verificar:

## Logs

- [ ] Sem credenciais.
- [ ] Sem tokens.
- [ ] Sem JWT.
- [ ] Sem connection strings.

---

## Traces

Verificar:

- [ ] Nenhum atributo contém senha.
- [ ] Nenhum atributo contém token.
- [ ] Nenhum atributo contém PII.

---

## Métricas

Verificar:

- [ ] Sem labels de alta cardinalidade.
- [ ] Sem IDs únicos.
- [ ] Sem emails.

Não aceitável:

```csharp
counter.Add(1,
    new("user_id", userId));
```

Aceitável:

```csharp
counter.Add(1,
    new("status", "approved"));
```

---

# Camada 8 — Dependências

Verificar:

## .NET

```bash
dotnet list package --vulnerable
```

---

## Python

```bash
pip-audit
```

ou

```bash
safety check
```

---

## Docker

```bash
docker scout quickview
```

ou

```bash
trivy image <image>
```

---

# Camada 9 — Hardening de Produção

Verificar:

- [ ] HTTPS obrigatório.
- [ ] CORS configurado.
- [ ] Security Headers configurados.
- [ ] Rate Limiting configurado.
- [ ] Healthchecks sem informações sensíveis.
- [ ] Swagger protegido fora de Development.
- [ ] Debug desabilitado.

---

# Checklist de Aprovação

Merge bloqueado se existir:

- Credencial exposta
- SQL Injection
- Mongo Injection
- Endpoint administrativo aberto
- JWT inseguro
- Dados sensíveis em logs
- Containers rodando como root

---

# Formato do Relatório

Para cada problema encontrado:

### [CRÍTICO | IMPORTANTE | MÉDIO]

**Arquivo**
`caminho/arquivo.cs`

**Problema**
Descrição clara do risco.

**Impacto**
O que pode acontecer em produção.

**Correção**
Como resolver.

**Exemplo**
Trecho sugerido.

---

# Resumo Final

Informar:

- Quantidade de problemas críticos
- Quantidade de problemas importantes
- Quantidade de problemas médios
- Aprovação ou reprovação do merge

Critérios:

✅ APROVADO
Nenhum problema crítico.

⚠ APROVADO COM RESSALVAS
Sem críticos, mas existem importantes.

❌ REPROVADO
Existe ao menos um problema crítico.