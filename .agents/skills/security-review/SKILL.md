---
name: security-review
description: >
  Use esta skill para revisar código, configurações,
  infraestrutura e observabilidade em busca de riscos
  de segurança e más práticas.

  Este projeto é um projeto pessoal/portfólio executado
  principalmente em ambiente local com Docker Compose.

  A revisão deve diferenciar claramente:
  - Vulnerabilidades reais
  - Melhorias recomendadas para produção
  - Decisões aceitáveis para ambiente local
---

# Skill: Security Review

## Objetivo

Realizar uma revisão de segurança pragmática e orientada a risco.

O foco é encontrar:

- vulnerabilidades reais
- exposição de segredos
- falhas de autenticação
- riscos de injeção
- vazamento de dados
- configurações inseguras

Sem gerar falsos positivos comuns em projetos pessoais.

---

# Contexto do Projeto

Antes de iniciar a revisão, assumir:

- Projeto pessoal
- Ambiente local
- Uso educacional
- Docker Compose
- Sem exposição pública conhecida

Portanto:

- `.env.example` com senhas fictícias é aceitável
- Credenciais de laboratório são aceitáveis
- Swagger aberto em ambiente local é aceitável
- RabbitMQ Management local é aceitável

Apenas reporte como problema quando:

- existir risco real
- existir segredo real exposto
- existir algo que impediria uso seguro em produção

---

# Classificação de Severidade

## CRÍTICO

Vulnerabilidade real.

Exemplos:

- segredo real commitado
- SQL Injection
- Mongo Injection
- JWT inseguro
- endpoint administrativo sem autenticação
- credenciais vazadas em logs
- execução remota possível

Deve ser corrigido imediatamente.

---

## IMPORTANTE

Não é vulnerabilidade imediata.

Mas dificulta uso seguro em produção.

Exemplos:

- container executando como root
- ausência de rate limiting
- ausência de autenticação
- ausência de HTTPS
- ausência de rotação de segredos

Deve entrar no backlog.

---

## SUGESTÃO

Melhoria de hardening.

Exemplos:

- headers de segurança
- CSP
- configurações mais restritivas
- melhorias de observabilidade

Não bloqueia merge.

---

# Camada 1 — Segredos

Verificar:

- [ ] .env não está commitado
- [ ] .gitignore ignora .env
- [ ] Segredos reais não estão em código
- [ ] Chaves JWT não estão hardcoded
- [ ] API Keys não estão hardcoded
- [ ] Connection strings não aparecem em logs

Não considerar:

- .env.example
- valores de laboratório
- exemplos fictícios

como vulnerabilidade.

---

# Camada 2 — APIs

Verificar:

- [ ] validação de entrada
- [ ] enums seguros
- [ ] IDs validados
- [ ] valores monetários validados
- [ ] mass assignment inexistente
- [ ] stacktrace não retorna ao cliente

### C#

Preferir:

```csharp
[Required]
[StringLength(200)]
```

ou FluentValidation.

### Python

Preferir:

```python
Field(gt=0)
Field(max_length=200)
```

---

# Camada 3 — Banco de Dados

## SQL Injection

Verificar:

- EF Core LINQ
- parâmetros
- consultas parametrizadas

Reportar apenas se houver concatenação de SQL.

---

## Mongo Injection

Verificar:

- filtros tipados
- queries construídas por objetos

Reportar apenas quando input do usuário controla diretamente a query.

---

# Camada 4 — RabbitMQ

Verificar:

- ACK explícito
- NACK explícito
- DLQ configurada
- Inbox Pattern
- Publisher Confirm

Reportar:

- ausência de idempotência
- perda silenciosa de mensagens

---

# Camada 5 — Logs, Traces e Métricas

Verificar:

### Logs

- senhas
- tokens
- connection strings
- JWT

### Traces

- atributos sensíveis

### Métricas

- IDs únicos
- emails
- CPF
- labels de alta cardinalidade

---

# Camada 6 — Docker

Verificar:

- container executa como root
- imagens extremamente antigas
- volumes excessivos

Importante:

Em projeto local isso normalmente é:

IMPORTANTE

não

CRÍTICO

---

# Camada 7 — Dependências

Verificar:

### .NET

```bash
dotnet list package --vulnerable
```

### Python

```bash
pip-audit
```

### Docker

```bash
trivy image <image>
```

Reportar apenas vulnerabilidades conhecidas relevantes.

---

# Camada 8 — Produção (Somente Recomendações)

Não marcar como crítico.

Apenas sugerir.

Verificar:

- HTTPS
- Rate Limiting
- Security Headers
- CORS
- Swagger protegido
- Health Checks mínimos

Classificação máxima:

IMPORTANTE

---

# Regras Especiais

## Não reportar

Não considere vulnerabilidade:

- .env.example
- localhost
- credenciais fictícias
- swagger aberto localmente
- rabbitmq management local
- mongodb exposto apenas na rede docker

---

## Reportar

Considere vulnerabilidade:

- segredo real commitado
- segredo real em log
- senha em trace
- token em métrica
- SQL Injection
- Mongo Injection
- autenticação quebrada

---

# Formato do Resultado

Por padrão:

Mostrar apenas no chat.

Não criar arquivos.

---

Somente criar arquivo markdown quando solicitado explicitamente:

Exemplos:

- "gere relatório"
- "salve relatório"
- "crie SECURITY_REVIEW.md"

---

# Formato

### [CRÍTICO | IMPORTANTE | SUGESTÃO]

**Arquivo**
`caminho/arquivo.cs`

**Problema**
Descrição objetiva.

**Impacto**
Consequência prática.

**Correção**
Como resolver.

---

# Resumo Final

Informar:

- Críticos
- Importantes
- Sugestões

Classificação:

✅ APROVADO
Sem críticos.

⚠ APROVADO COM RESSALVAS
Sem críticos, mas existem importantes.

❌ REPROVADO
Existe ao menos um crítico.

A revisão deve ser objetiva.

Evitar relatórios excessivamente longos.

Priorizar qualidade sobre quantidade.