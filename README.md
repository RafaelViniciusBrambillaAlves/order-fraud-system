<div align="center">

# 🛒 Order Fraud System

### Projeto de estudo de microsserviços em nível de produção, com arquitetura distribuída, mensageria assíncrona, observabilidade e padrões de resiliência

<br/>

![.NET](https://img.shields.io/badge/.NET_8-512BD4?style=for-the-badge&logo=dotnet&logoColor=white)
![C#](https://img.shields.io/badge/C%23-239120?style=for-the-badge&logo=csharp&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL_Server-CC2927?style=for-the-badge&logo=microsoftsqlserver&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<br/>

![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)
![Jaeger](https://img.shields.io/badge/Jaeger-66CFE3?style=for-the-badge&logo=jaeger&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)
![Traefik](https://img.shields.io/badge/Traefik-24A1C1?style=for-the-badge&logo=traefikproxy&logoColor=white)
![Polly](https://img.shields.io/badge/Polly-512BD4?style=for-the-badge&logo=dotnet&logoColor=white)
![Entity Framework](https://img.shields.io/badge/EF_Core-512BD4?style=for-the-badge&logo=dotnet&logoColor=white)

<br/>

![Microservices](https://img.shields.io/badge/Microservices-Architecture-blue?style=for-the-badge)
![Clean Architecture](https://img.shields.io/badge/Clean-Architecture-green?style=for-the-badge)
![Saga Pattern](https://img.shields.io/badge/Saga-Pattern-orange?style=for-the-badge)
![Outbox Pattern](https://img.shields.io/badge/Outbox-Pattern-red?style=for-the-badge)
![Inbox Pattern](https://img.shields.io/badge/Inbox-Pattern-purple?style=for-the-badge)
![EDA](https://img.shields.io/badge/Event_Driven-Architecture-yellow?style=for-the-badge)
![Async Messaging](https://img.shields.io/badge/Async-Messaging-cyan?style=for-the-badge)

</div>

---

## 📋 Sumário

1. [Conceitos Fundamentais sobre Microserviços](#-conceitos-fundamentais-sobre-microserviços)
2. [Introdução](#-introdução)
3. [Objetivos do Projeto](#-objetivos-do-projeto)
4. [Arquitetura do Sistema](#-arquitetura-do-sistema)
5. [Estrutura do Projeto](#-estrutura-do-projeto)
6. [Tecnologias Utilizadas](#-tecnologias-utilizadas)
7. [Pré-requisitos](#-pré-requisitos)
8. [Executando o Projeto](#-executando-o-projeto)
9. [Endpoints e Acessos](#-endpoints-e-acessos)
10. [RabbitMQ e Mensageria Assíncrona](#-rabbitmq-e-mensageria-assíncrona)
11. [Resiliência](#-resiliência)
12. [Transactional Outbox Pattern](#-transactional-outbox-pattern)
13. [Inbox Pattern e Idempotência](#-inbox-pattern-e-idempotência)
14. [Saga Pattern](#-saga-pattern)
15. [Timeout de Saga](#-timeout-de-saga)
16. [API Gateway](#-api-gateway)
17. [Persistência Poliglota](#-persistência-poliglota)
18. [Observabilidade](#-observabilidade)
19. [Traces Distribuídos no Jaeger](#-traces-distribuídos-no-jaeger)
20. [Dashboards do Grafana](#-dashboards-do-grafana)
21. [Alertas no Grafana](#-alertas-no-grafana)
22. [Logs Centralizados com Loki](#-logs-centralizados-com-loki)
23. [Testes de Resiliência](#-testes-de-resiliência)
24. [Melhorias Implementadas](#-melhorias-implementadas)
25. [Conceitos Aplicados](#-conceitos-aplicados)
27. [Referências e Materiais de Estudo](#-referências-e-materiais-de-estudo)
26. [Conclusão](#-conclusão)

---

## 🧭 Conceitos Fundamentais sobre Microserviços

Microsserviços são uma abordagem arquitetural em que um sistema é dividido em serviços pequenos, autônomos e orientados a capacidades de negócio. Cada serviço deve ter uma responsabilidade clara, possuir seu próprio ciclo de desenvolvimento, ser implantável de forma independente e se comunicar com outros serviços por contratos bem definidos, como APIs HTTP, eventos ou mensagens assíncronas.

Mais do que uma escolha técnica, microsserviços representam uma forma diferente de organizar software, times e operação. A arquitetura só entrega valor quando vem acompanhada de boas práticas de engenharia, automação, observabilidade, governança de contratos e uma cultura forte de responsabilidade ponta a ponta.

### Princípios centrais

- **Autonomia** — cada serviço deve conseguir evoluir, ser testado e ser implantado com o mínimo de dependência direta de outros serviços.
- **Baixo acoplamento** — serviços devem conhecer contratos, não detalhes internos uns dos outros.
- **Alta coesão** — cada serviço deve concentrar regras relacionadas a uma capacidade específica de negócio.
- **Dono dos próprios dados** — cada serviço deve controlar seu modelo de dados, evitando banco compartilhado e dependência direta de schema.
- **Comunicação por contratos** — integrações devem ser explícitas, versionáveis e observáveis.
- **Falhas esperadas** — indisponibilidade parcial, latência, duplicidade de mensagens e timeouts não são exceções raras; fazem parte do modelo operacional.

### Vantagens

Quando bem aplicados, microsserviços ajudam a escalar sistemas e organizações:

- **Escalabilidade independente** — partes críticas do sistema podem escalar separadamente, sem replicar toda a aplicação.
- **Deploy independente** — mudanças em um serviço podem ir para produção sem exigir o deploy coordenado do sistema inteiro.
- **Isolamento de falhas** — uma falha localizada pode ser contida, evitando derrubar toda a plataforma.
- **Flexibilidade tecnológica** — cada serviço pode usar a tecnologia mais adequada ao seu problema, desde que respeite os contratos de integração.
- **Evolução por domínio** — times conseguem trabalhar alinhados a capacidades de negócio, com ownership mais claro.
- **Manutenibilidade em escala** — bases de código menores tendem a ser mais fáceis de entender, testar e evoluir.

### Dificuldades e custos reais

Microsserviços não simplificam um sistema automaticamente; eles deslocam parte da complexidade para a comunicação, operação e consistência entre serviços.

- **Complexidade distribuída** — chamadas de rede falham, mensagens atrasam, consumidores caem e respostas podem chegar fora de ordem.
- **Consistência eventual** — nem sempre todos os serviços enxergam o mesmo estado ao mesmo tempo.
- **Observabilidade obrigatória** — logs isolados não bastam; é preciso correlacionar traces, métricas e logs entre serviços.
- **Testes mais difíceis** — além de testes unitários e de integração, contratos e fluxos ponta a ponta precisam ser validados.
- **Operação mais exigente** — deploy, rollback, health checks, tracing, alertas e monitoramento se tornam parte essencial da arquitetura.
- **Governança de contratos** — mudanças em eventos, rotas, payloads e schemas precisam ser compatíveis para não quebrar consumidores.
- **Risco de fragmentação** — sem padrões mínimos, cada serviço pode virar uma ilha com práticas, bibliotecas e modelos inconsistentes.

### Cultura necessária

Adotar microsserviços exige maturidade de engenharia. O time que constrói um serviço também deve entender como ele roda, falha, escala e se recupera em produção.

- **You build it, you run it** — o time responsável pelo serviço também acompanha sua operação.
- **Automação como padrão** — build, testes, migrations, provisionamento e deploy devem ser automatizados.
- **Observabilidade desde o início** — métricas, traces e logs não são complementos; são parte do desenho do serviço.
- **Contratos bem definidos** — APIs e eventos precisam ser tratados como produtos consumidos por outros times ou serviços.
- **Resiliência por design** — retry, timeout, DLQ, idempotência e circuit breaker devem ser decisões explícitas.
- **Documentação objetiva** — decisões arquiteturais, fluxos e integrações precisam estar claros para reduzir dependência de conhecimento tribal.

### Quando microsserviços fazem sentido

Microsserviços tendem a fazer sentido quando o domínio é grande o suficiente para justificar fronteiras claras, quando existem times diferentes trabalhando em partes independentes do produto, quando a escala de deploy ou de carga varia bastante entre módulos e quando a organização tem maturidade operacional para lidar com sistemas distribuídos.

Eles não são a melhor primeira escolha para todo projeto. Em sistemas pequenos, com domínio ainda instável ou equipe reduzida, um monólito bem modularizado costuma ser mais simples, barato e eficiente. A extração para microsserviços deve ser uma resposta a uma necessidade real de escala, autonomia, isolamento ou evolução organizacional, não apenas uma decisão estética.

### Relação com este projeto

Este projeto foi desenhado para demonstrar justamente os pontos que tornam microsserviços poderosos e difíceis ao mesmo tempo: serviços independentes, bancos separados, comunicação assíncrona, consistência eventual, tolerância a falhas, idempotência, rastreamento distribuído, métricas operacionais e logs centralizados. Cada padrão implementado aqui existe para tratar um problema comum em arquiteturas distribuídas reais.

---

## 🚀 Introdução

Este projeto é um estudo avançado de **arquitetura de microsserviços distribuídos** aplicada a um sistema realista de processamento de pedidos com análise antifraude. Ele foi construído para ir além de tutoriais básicos, modelando desafios comuns em sistemas distribuídos de nível de produção: perda de mensagens, processamento duplicado, coordenação de sagas, observabilidade entre serviços e comunicação resiliente.

O sistema simula o **ciclo de vida de um pedido de e-commerce**: o cliente cria um pedido, a análise antifraude é executada de forma assíncrona, e o pedido é aprovado ou rejeitado. A superfície parece simples, mas a engenharia por trás é intencionalmente profunda.

Os dois serviços são poliglotas por design:

- **order-service** — desenvolvido com `.NET 8` e `C#`, persiste dados no `SQL Server` via `Entity Framework Core`
- **fraud-service** — desenvolvido com `Python` e `FastAPI`, persiste dados no `MongoDB` via `Motor`

Eles se comunicam exclusivamente por meio do `RabbitMQ`, sem chamadas HTTP diretas entre serviços. Essa decisão arquitetural reforça o desacoplamento e demonstra como uma **Event-Driven Architecture (EDA)** funciona na prática.

### Por que este projeto importa

Em sistemas distribuídos, os problemas mais difíceis não estão em escrever código, mas em lidar com falhas:

- E se o RabbitMQ estiver temporariamente indisponível no momento da publicação?
- E se o fraud-service cair no meio do processamento e a mensagem for reenviada?
- E se a mesma mensagem chegar duas vezes por causa de uma retentativa de rede?
- E se o fraud-service nunca responder? Quanto tempo o sistema deve esperar?
- Como depurar uma falha que atravessa 4 serviços e aconteceu de forma assíncrona?

Cada padrão e implementação deste projeto existe para responder a uma dessas perguntas.

---

## 🎯 Objetivos do Projeto

Este projeto foi construído como um laboratório prático para os seguintes temas avançados de backend e sistemas distribuídos:

| Categoria | Tópicos abordados |
|---|---|
| **Arquitetura** | Microsserviços, Clean Architecture, Separação de Responsabilidades, Injeção de Dependência |
| **Mensageria** | RabbitMQ, Exchange, Queue, Binding, Routing Key, Filas Duráveis, ACK/NACK |
| **Confiabilidade** | Publisher Confirms, DLQ, Retry, Reconexão, Consumidores Resilientes |
| **Padrões** | Transactional Outbox, Inbox, Saga (Coreografia), Idempotência |
| **Observabilidade** | OpenTelemetry, Distributed Tracing, Métricas, Logs Centralizados |
| **Ferramentas** | Jaeger, Prometheus, Grafana, Loki, Traefik, Docker Compose |
| **Persistência** | Persistência Poliglota — SQL Server + MongoDB |
| **Consistência** | Consistência Eventual, Entrega At-Least-Once, Processamento Exactly-Once |

---

## 🏗 Arquitetura do Sistema

### Arquitetura de Alto Nível

![System Architecture](img/system-architecture.png)

O sistema é composto por dois microsserviços autônomos, cada um com seu próprio banco de dados, comunicando-se exclusivamente por RabbitMQ. Não há chamada HTTP direta entre serviços em tempo de execução.

```text
Client/Browser -> Traefik API Gateway -> order-service (.NET/C# + SQL Server)
                                      -> RabbitMQ Events -> fraud-service (Python/FastAPI + MongoDB)
```

**Principais decisões de design:**

- **Sem acoplamento síncrono entre serviços** — a análise antifraude é sempre assíncrona
- **Cada serviço é dono dos seus dados** — sem banco compartilhado e sem schema compartilhado
- **Infraestrutura como código** — a topologia do RabbitMQ é declarada em `definitions.json`
- **Ponto único de entrada** — o Traefik roteia todo o tráfego externo
- **Observabilidade completa** — serviços emitem traces, métricas e logs estruturados para uma stack centralizada

### Fluxo do Sistema

![System Flow](img/system-flow.png)

Ciclo completo do pedido entre os serviços:

```text
[Client]
    |
    v POST /api/orders
[order-service]
    | 1. Persiste Order (Status: PENDING_FRAUD_CHECK)
    | 2. Persiste OutboxMessage (Status: PENDING)      <- mesma transação
    |
    v [OutboxRelayWorker consulta a cada 500ms]
    | 3. Publica OrderCreatedEvent -> exchange order.events
    | 4. Order.SagaStartedAt = UtcNow
    |
    v RabbitMQ roteia para fraud.analysis.queue
[fraud-service]
    | 5. Consome OrderCreatedEvent
    | 6. Verifica Inbox (idempotência)
    | 7. Analisa fraude (regra de limite por valor)
    | 8. Persiste Order + OutboxMessage (mesma transação)
    |
    v [OutboxRelayWorker consulta]
    | 9. Publica OrderAnalyzedEvent -> exchange fraud.events
    |    routing key: order.approved | order.rejected
    |
    v RabbitMQ roteia para order.result.queue
[order-service]
    | 10. OrderResultWorker consome o evento
    | 11. OrderAnalyzedEventHandler verifica Inbox
    | 12. Atualiza status do pedido (APPROVED | REJECTED)
    | 13. Registra InboxMessage              <- mesma transação
    | 14. Registra métrica SagaDuration
    v
[Saga Complete]
```

---

## 📁 Estrutura do Projeto

```text
order-fraud-system/
|
|-- docker-compose.yml                    # Orquestração completa da stack
|
|-- order-service/                        # Microsserviço .NET 8
|   |-- Dockerfile
|   |-- .env / .env.example
|   `-- OrderService/
|       |-- order-service.API/            # Entrada HTTP, Swagger e DI
|       |-- order-service.Application/    # Casos de uso, serviços, eventos e workers
|       |-- order-service.Domain/         # Modelo de negócio puro
|       `-- order-service.Infrastructure/ # EF Core, RabbitMQ e OTel
|
|-- fraud-service/                        # Microsserviço Python 3.11 / FastAPI
|   |-- Dockerfile
|   |-- .env / .env.example
|   `-- app/                              # API, aplicação, domínio, infraestrutura, mensageria e observabilidade
|
|-- rabbitmq/
|   |-- definitions.json                  # Exchanges, filas e bindings pré-declarados
|   `-- rabbitmq.conf
|
|-- mongodb/
|   `-- mongo-init.sh                     # Inicialização do replica set para transações
|
`-- observability/
    |-- otel-collector.yml                # Pipeline do Collector
    |-- prometheus.yml                    # Configuração de scrape
    `-- grafana/                          # Provisionamento e dashboards
```

### Clean Architecture no order-service

O serviço .NET segue Clean Architecture com regras de dependência apontando para dentro:

```text
API  ->  Application  ->  Domain
 |             |              ^
 `-------------+------------> Infrastructure
```

- **Domain** — entidades (`Order`, `OutboxMessage`, `InboxMessage`), enums e interfaces de repositório. Sem dependência de infraestrutura ou frameworks.
- **Application** — regras de negócio, casos de uso, handlers de eventos e workers em background. Depende apenas de Domain.
- **Infrastructure** — EF Core, RabbitMQ e OpenTelemetry. Implementa as interfaces definidas no domínio.
- **API** — camada HTTP, Swagger e registro de dependências.

Isso significa que `OrderService.cs`, na camada Application, nunca importa RabbitMQ. Ele grava no Outbox, e o relay da infraestrutura faz a publicação real. **A regra de negócio fica totalmente isolada do mecanismo de transporte.**

---

## 🛠 Tecnologias Utilizadas

| Tecnologia | Finalidade | Onde é usada | Principal benefício |
|---|---|---|---|
| **.NET 8 / C#** | Runtime do order-service | order-service | Performance, tipagem forte e ecossistema maduro |
| **Python 3.11 / FastAPI** | Runtime do fraud-service | fraud-service | I/O assíncrono, desenvolvimento rápido e validação com Pydantic |
| **RabbitMQ** | Broker de mensagens assíncronas | Ambos os serviços | Durabilidade, roteamento, entrega at-least-once e DLQ |
| **SQL Server** | Persistência relacional | order-service | Transações ACID, migrations EF e atomicidade do Outbox |
| **MongoDB** | Persistência documental | fraud-service | Schema flexível e sessões nativas para transações |
| **Entity Framework Core** | ORM | order-service | Migrations, LINQ e rastreamento de alterações |
| **Motor (async pymongo)** | Driver assíncrono do MongoDB | fraud-service | I/O totalmente assíncrono e suporte a sessões |
| **Polly** | Biblioteca de resiliência | order-service | Retry pipelines e exponential backoff |
| **OpenTelemetry** | SDK de observabilidade | Ambos os serviços | Instrumentação neutra em relação ao fornecedor |
| **OTEL Collector** | Pipeline de telemetria | Infra | Exportação desacoplada, batching e filtragem |
| **Jaeger** | Tracing distribuído | Infra | Visualização completa de traces entre serviços |
| **Prometheus** | Armazenamento de métricas | Infra | Séries temporais, scraping e regras de alerta |
| **Grafana** | Dashboards e alertas | Infra | Visualização unificada de métricas, traces e logs |
| **Loki + Promtail** | Agregação de logs | Infra | Leve, baseado em labels e com LogQL |
| **Traefik** | API Gateway / Reverse proxy | Infra | Auto-discovery via Docker e regras de roteamento |
| **Docker / Compose** | Containerização | Todos | Ambientes reproduzíveis e isolamento de serviços |

---

## ✅ Pré-requisitos

- **Docker** >= 24.0 e **Docker Compose** >= 2.x
- Portas disponíveis: `80`, `5672`, `15672`, `1433`, `27017`, `16686`, `9090`, `3001`, `3000`, `8080`
- Pelo menos **6 GB de RAM** alocados ao Docker

Para desenvolvimento local fora do Docker:

- **.NET SDK** 8.0.x
- **Python** 3.11+

---

## ▶️ Executando o Projeto

### 1. Clone o repositório

```bash
git clone https://github.com/RafaelViniciusBrambillaAlves/order-fraud-system
cd order-fraud-system
```

### 2. Configure as variáveis de ambiente

```bash
# order-service
cp order-service/.env.example order-service/.env

# fraud-service
cp fraud-service/.env.example fraud-service/.env
```

Edite cada `.env` com suas credenciais. Os arquivos `.env.example` documentam todas as variáveis.

**order-service `.env`:**
```env
ASPNETCORE_ENVIRONMENT=Development
ASPNETCORE_URLS=http://+:80
ConnectionStrings__DefaultConnection=Server=sqlserver,1433;Database=OrderDb;User Id=sa;Password=YourStrong!Passw0rd;TrustServerCertificate=True;Encrypt=False;
RabbitMq__Host=rabbitmq
RabbitMq__Port=5672
RabbitMq__Username=admin
RabbitMq__Password=admin123
Observability:OtlpEndpoint=http://otel-collector:4317
```

**fraud-service `.env`:**
```env
MONGODB_URL=mongodb://mongodb:27017/frauddb?replicaSet=rs0
MONGODB_DATABASE=fraud_db
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin123
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
OTLP_ENDPOINT=http://otel-collector:4317
```

### 3. Suba a stack

```bash
docker compose up --build -d
```

A ordem de inicialização é tratada automaticamente por `healthcheck` + `depends_on`. SQL Server e MongoDB levam mais tempo para iniciar. O order-service aplica migrations do EF automaticamente via `ApplyMigrationsAsync()`.

### 4. Verifique os serviços

```bash
docker compose ps
```

Todos os serviços devem aparecer como `healthy` ou `running`. Se `order-service` reiniciar algumas vezes, o SQL Server ainda pode estar subindo; ele deve se recuperar automaticamente.

---

## 🌐 Endpoints e Acessos

| Serviço | URL | Descrição |
|---|---|---|
| **order-service API** | `http://localhost/api/orders` | API REST via Traefik |
| **order-service Swagger** | `http://localhost/order/swagger` | Documentação da API |
| **fraud-service API** | `http://localhost/api/fraud/orders` | API REST via Traefik |
| **fraud-service Docs** | `http://localhost/fraud/docs` | Documentação automática do FastAPI |
| **RabbitMQ UI** | `http://localhost:15672` | User: `admin` / Pass: `admin123` |
| **Jaeger** | `http://localhost:16686` | Traces distribuídos |
| **Prometheus** | `http://localhost:9090` | Métricas brutas |
| **Grafana** | `http://localhost:3001` | Dashboards e alertas |
| **DbGate (SQL UI)** | `http://localhost:3000` | Explorador do SQL Server |
| **Traefik Dashboard** | `http://localhost:8080` | Visão geral do roteamento |

**Conexão DbGate:** Type: SQL Server | Server: `sqlserver` | Port: `1433` | User: `sa` | Password: `YourStrong!Passw0rd` | Database: `OrderDb`

### Criando um pedido (teste rápido)

```bash
curl -X POST http://localhost/api/orders \
  -H "Content-Type: application/json" \
  -d '{"description": "Test order", "amount": 500.00}'
```

- Amount <= 1000 -> `APPROVED`
- Amount > 1000 -> `REJECTED`

```bash
# Check status
curl http://localhost/api/orders/{id}
```

---

## 📨 RabbitMQ e Mensageria Assíncrona

### Visão geral da arquitetura

![Consumer Flow](img/consumer.png)

O RabbitMQ é a espinha dorsal da comunicação entre serviços. Entender seus conceitos é essencial para entender este projeto.

### Exchange — o roteador

Uma Exchange **nunca armazena mensagens**. Ela recebe a mensagem publicada e decide para quais filas enviá-la com base nas regras de roteamento.

Este projeto usa **Direct Exchange**, o tipo de roteamento mais preciso: entrega para a fila cujo binding possui exatamente a mesma routing key.

```text
order-service publica -> exchange "order.events", key "order.created"
                        Exchange procura binding para "order.created"
                                    |
                                    v
                          fraud.analysis.queue <- binding registrado aqui
```

Duas exchanges principais são definidas em `definitions.json`:

| Exchange | Tipo | Uso |
|---|---|---|
| `order.events` | Direct | order-service -> fraud-service |
| `fraud.events` | Direct | fraud-service -> order-service |
| `dead.letter.exchange` | Direct | Mensagens com falha -> DLQ |

### Queue — o buffer

Filas mantêm mensagens até que um consumidor as processe. Todas as filas deste projeto são declaradas com:

- `durable: true` — a fila sobrevive a reinicializações do RabbitMQ
- `DeliveryMode: 2` — cada mensagem também é persistida em disco

Sem `durable: true`, o RabbitMQ perde filas ao reiniciar. Sem `DeliveryMode: 2`, mesmo filas duráveis podem perder mensagens em memória se o broker cair antes de gravar em disco.

### Bindings — conectando exchanges a filas

Um binding é a regra de roteamento. Sem binding, uma mensagem publicada não tem destino e pode ser descartada.

```text
exchange: "order.events" + routing_key: "order.created"  ->  queue: "fraud.analysis.queue"
exchange: "fraud.events" + routing_key: "order.approved" ->  queue: "order.result.queue"
exchange: "fraud.events" + routing_key: "order.rejected" ->  queue: "order.result.queue"
```

### ACK / NACK — confirmação de entrega

O RabbitMQ não remove uma mensagem da fila assim que ela é entregue; ele espera uma confirmação:

- **BasicAck** — processamento concluído com sucesso, remove a mensagem da fila
- **BasicNack(requeue: false)** — processamento falhou, envia para a DLQ em vez de recolocar na fila

`requeue: false` é essencial. Com `requeue: true`, uma mensagem com erro volta para o início da fila e pode criar um loop infinito de retentativas.

### Dead Letter Queue (DLQ)

Quando uma mensagem recebe NACK, expira ou é rejeitada, o RabbitMQ a roteia para a **Dead Letter Exchange** e depois para a DLQ correspondente.

DLQs usam TTL de 7 dias (`x-message-ttl: 604800000ms`), permitindo inspeção e reprocessamento. Cada serviço possui um `DlqWorker` dedicado, que monitora sua DLQ, registra dead letters com contexto completo, emite métricas e mantém um hook virtual (`OnDeadLetterReceivedAsync`) para integrações futuras.

### Publisher Confirms

O `RabbitMqPublisher` usa `channel.ConfirmSelect()` e `WaitForConfirms(5s)`. O fluxo é:

1. Publicar mensagem no broker
2. Aguardar confirmação de que o broker persistiu a mensagem
3. Só então marcar a mensagem como publicada no Outbox

Sem publisher confirms, a aplicação pode acreditar que enviou a mensagem mesmo que o broker a tenha descartado. Com confirms, há **entrega at-least-once do publisher para o broker**.

### Topologia gerenciada pela infraestrutura

> **Decisão arquitetural importante:** exchanges, filas e bindings **não são declarados pelos serviços**. Eles são pré-declarados em `rabbitmq/definitions.json` e carregados na inicialização do broker.

Isso evita um anti-pattern perigoso: se dois serviços tentarem declarar a mesma fila com argumentos diferentes, o RabbitMQ lança erro de canal e encerra a conexão. Centralizar a topologia torna a configuração explícita, versionada e previsível.

---

## 🛡 Resiliência

Resiliência em sistemas distribuídos significa degradar com controle e recuperar automaticamente quando componentes falham.

### Gerenciamento de conexão com Polly

`RabbitMqPublisher` e `RabbitMqSubscriber` usam pipelines de resiliência com Polly:

```csharp
private static readonly ResiliencePipeline RetryPipeline = new ResiliencePipelineBuilder()
    .AddRetry(new RetryStrategyOptions
    {
        MaxRetryAttempts = 5,
        Delay = TimeSpan.FromSeconds(2),
        BackoffType = DelayBackoffType.Exponential,
        ShouldHandle = new PredicateBuilder()
            .Handle<BrokerUnreachableException>()
            .Handle<AlreadyClosedException>()
    })
    .Build();
```

**Exponential backoff** significa tentar novamente após 2s, 4s, 8s, 16s e 32s. Isso evita que várias instâncias pressionem o broker ao mesmo tempo durante uma reinicialização.

### Conexão lazy

Os serviços não dependem do RabbitMQ estar pronto no startup. `EnsureChannelIsOpen()` é chamado por operação; se o canal estiver fechado, ele reconecta antes de tentar publicar ou consumir.

Isso permite que:

- Serviços subam mesmo que o RabbitMQ ainda não esteja pronto
- Desconexões temporárias sejam recuperadas sem reiniciar o serviço
- O endpoint `/health` possa retornar `200 OK` enquanto aguarda o broker

### Loop de consumidor resiliente

`OutboxRelayWorker` roda em loop e trata explicitamente:

- `asyncio.CancelledError` — sinal de shutdown limpo
- `aio_pika.exceptions.AMQPConnectionError` — broker indisponível; mensagens permanecem `PENDING`
- `Exception` genérica — erro é registrado e o loop continua

Por isso o Outbox Pattern é fundamental: se o RabbitMQ cair, o pedido ainda é criado e salvo. O relay publicará quando o broker voltar.

---

## 📦 Transactional Outbox Pattern

![Outbox Pattern](img\relay-strategy.png)

### O problema: Dual-Write

Sempre que a aplicação executa duas operações independentes — salvar no banco **e** publicar no RabbitMQ — existe risco de inconsistência. Essas operações não participam da mesma transação ACID.

```text
Cenário de falha Dual-Write:

1. order.SaveChanges()    <- SUCESSO — linha gravada no SQL Server
2. rabbitMQ.Publish()     <- FALHA — broker indisponível ou timeout

Resultado: o pedido existe no banco, mas o fraud-service nunca é notificado.
           O pedido fica preso em PENDING_FRAUD_CHECK.
```

### A solução: Transactional Outbox

Em vez de publicar diretamente no broker, a aplicação persiste a **intenção de publicação** na mesma transação dos dados de negócio:

```csharp
// OrderService.cs — tudo em uma transação atômica
await _orderRepository.AddAsync(order, cancellationToken);          // dado de negócio
await _outboxRepository.AddAsync(outboxMessage, cancellationToken); // intenção de publicação
await _orderRepository.SaveChangesAsync(cancellationToken);         // commit único
```

Se o commit falhar, as duas gravações são revertidas. Se ele tiver sucesso, as duas linhas existem, e o relay publicará o evento posteriormente.

### O relay worker

`OutboxRelayWorker` roda como background service, consultando a cada 500ms:

```text
1. SELECT TOP 50 * FROM OutboxMessages WHERE Status = PENDING ORDER BY CreatedAt
2. Para cada mensagem:
   a. BasicPublish para RabbitMQ
   b. WaitForConfirms (publisher confirms)
   c. UPDATE OutboxMessages SET Status = SENT, SentAt = NOW()
3. Se a publicação falhar: incrementa RetryCount e marca FAILED após 5 tentativas
```

### Estratégias de relay

| Estratégia | Como funciona | Latência | Complexidade | Melhor uso |
|---|---|---|---|---|
| **Polling** (implementado aqui) | Worker consulta o banco em intervalos | ~500ms | Baixa | Dev/carga moderada |
| **CDC via Debezium** | Lê o WAL em tempo real | ~10ms | Alta | Produção em alta escala |

### Resultados de resiliência

| Cenário | Antes do Outbox Pattern | Depois do Outbox Pattern |
|---|---|---|
| RabbitMQ fora durante criação do pedido | Evento perdido permanentemente | Evento salvo e publicado na recuperação |
| Serviço cai após commit no banco | Evento perdido permanentemente | Relay republica no restart |
| Broker reinicia | Intervenção manual necessária | Recuperação automática |

---

## 📬 Inbox Pattern e Idempotência

### O problema: At-Least-Once Delivery

O RabbitMQ garante **entrega at-least-once**. Em cenários de falha, a mesma mensagem pode ser entregue mais de uma vez. Sem proteção, o mesmo resultado antifraude poderia ser aplicado duas vezes.

### A solução: Inbox Pattern

Antes de processar qualquer evento, o handler verifica se aquele `EventId` já foi processado:

```csharp
var alreadyProcessed = await _inboxRepository.ExistsAsync(eventId, cancellationToken);

if (alreadyProcessed)
{
    return;
}
```

Se ainda não foi processado, o handler executa a lógica e registra o `EventId` **na mesma transação**:

```csharp
order.UpdateStatus(newStatus);

await _inboxRepository.AddAsync(new InboxMessage(eventId), cancellationToken);
await _inboxRepository.SaveChangesAsync(cancellationToken);
```

### Por que a mesma transação importa

Se a atualização do pedido e o registro do Inbox fossem commits separados, uma queda entre eles permitiria reprocessamento duplicado. Com um único `SaveChanges()`, as duas alterações são confirmadas juntas ou nenhuma delas é.

### Proteção no banco

A tabela `InboxMessages` possui `UNIQUE INDEX` em `EventId`. Mesmo se duas threads passarem pelo `ExistsAsync()` simultaneamente, o banco rejeita o segundo `INSERT`.

---

## 🔄 Saga Pattern

### Saga por Coreografia Orientada a Eventos

Uma **Saga** é uma sequência de transações locais que implementa uma transação de negócio distribuída. Este projeto usa a variante de **Coreografia**, sem orquestrador central. Cada serviço reage a eventos e publica o próximo evento da cadeia.

![System Flow](img/system-flow.png)

```text
order-service              RabbitMQ               fraud-service
Create Order
     |
     |-- Publish OrderCreated --> order.events --> Consume
                                                  |
                                             Analyze Fraud
                                                  |
                                             Publish OrderAnalyzed
                                             --> fraud.events
     |
Consume OrderAnalyzed <----------------------------
     |
Update Order Status
(APPROVED | REJECTED)
Saga Complete
```

### Rastreamento de estado da saga

A entidade `Order` acompanha o ciclo de vida da saga:

```csharp
public DateTime? SagaStartedAt { get; private set; }
public DateTime? SagaCompletedAt { get; private set; }
```

Isso permite:

- **Detecção de timeout** — comparar `SagaStartedAt` com o horário atual
- **Métricas de duração** — `SagaCompletedAt - SagaStartedAt`
- **Detecção de sagas órfãs** — `SagaStartedAt != null && SagaCompletedAt == null`

### Benefícios da coreografia sobre orquestração

| Aspecto | Coreografia (este projeto) | Orquestração |
|---|---|---|
| Acoplamento | Serviços conhecem apenas eventos | Serviços conhecem o orquestrador |
| Isolamento de falhas | Cada serviço lida com suas falhas | Falha do orquestrador afeta todas as sagas |
| Escalabilidade | Cada serviço escala de forma independente | Orquestrador pode virar gargalo |
| Complexidade | Fluxo completo é mais difícil de rastrear | Fluxo é mais fácil de visualizar |
| Observabilidade | Tracing distribuído é crítico | Estado centralizado fica visível no orquestrador |

---

## ⏱ Timeout de Saga

![Saga Timeout](img/saga-timeout.png)

### O problema: Sagas órfãs

Sem timeout, uma saga iniciada que nunca recebe resposta fica em `PENDING_FRAUD_CHECK` indefinidamente. Isso pode acontecer quando:

- o fraud-service cai antes de processar
- a mensagem vai para a DLQ e nunca é reprocessada
- uma partição de rede impede a entrega

Essas sagas acumulam no banco, inflam a métrica de pedidos pendentes e representam dinheiro parado em limbo operacional.

### A solução: SagaTimeoutWorker

`SagaTimeoutWorker` roda em background e verifica a cada 1 minuto pedidos em `PENDING_FRAUD_CHECK` há mais de 5 minutos:

```csharp
FraudAnalysisTimeout = TimeSpan.FromMinutes(5)
CheckInterval = TimeSpan.FromMinutes(1)
```

Ao encontrar pedidos expirados, executa `order.MarkAsTimedOut()`, definindo `Status = TIMED_OUT` e `SagaCompletedAt = UtcNow`.

### Tratamento de resposta tardia

Se o fraud-service responder depois do timeout, `OrderAnalyzedEventHandler` ignora a resposta:

```csharp
if (order.Status == OrderStatus.TIMED_OUT)
{
    return;
}
```

Isso evita corrida entre o worker de timeout e o consumidor do resultado antifraude.

---

## 🔀 API Gateway

![API Gateway](img/api-gateway-schema.png)

### Antes e depois

```text
Antes (acesso direto aos serviços):
  order-service:  http://localhost:5001/swagger
  fraud-service:  http://localhost:8000/docs

Depois (via Traefik gateway):
  order-service:  http://localhost/order/swagger
  fraud-service:  http://localhost/fraud/docs
  API:            http://localhost/api/orders
```

### Por que um API Gateway importa

Em produção, clientes não devem conhecer endereços internos de microsserviços. Esses endereços mudam com deploys, escala e reinicializações. O API Gateway fornece:

- **Ponto único de entrada** — todo tráfego passa por `localhost:80`
- **Roteamento** — o Traefik lê Docker labels e roteia automaticamente
- **Desacoplamento** — serviços podem ser movidos, escalados ou substituídos sem alterar clientes
- **Observabilidade** — todo tráfego fica visível no nível do gateway

### Configuração do Traefik via Docker labels

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.order.rule=PathPrefix(`/api/orders`)"
  - "traefik.http.routers.order.entrypoints=web"
  - "traefik.http.services.order.loadbalancer.server.port=80"
  - "traefik.http.routers.order-swagger.rule=PathPrefix(`/order/swagger`)"
  - "traefik.http.middlewares.order-swagger-rewrite.replacepathregex.regex=^/order/swagger(.*)"
  - "traefik.http.middlewares.order-swagger-rewrite.replacepathregex.replacement=/swagger$$1"
```

O Traefik descobre containers automaticamente e aplica as regras sem mudanças em arquivo de configuração central.

---

## 🗄 Persistência Poliglota

Problemas diferentes pedem bancos diferentes. Usar a ferramenta adequada para cada serviço é um princípio central de microsserviços.

### SQL Server no order-service

**Por quê:** o ciclo de vida do pedido envolve transições de estado que exigem **transações ACID**. O Transactional Outbox Pattern requer gravar `Orders` e `OutboxMessages` em um único commit atômico, algo que um banco relacional oferece com confiabilidade.

**Como:** Entity Framework Core com migrations code-first. Tabelas principais: `Orders`, `OutboxMessages`, `InboxMessage`. Índices parciais em `OutboxMessages` e `Orders` mantêm as consultas rápidas.

### MongoDB no fraud-service

**Por quê:** dados de análise antifraude são documentais e flexíveis. Transações multi-documento com sessões permitem gravar `orders` e `outbox_messages` atomicamente, como o Outbox Pattern exige.

**Como:** Motor com replica set (`replicaSet=rs0`). O replica set é necessário para transações multi-documento. Há índices em `outbox_messages` e `inbox_messages`.

---

## 🔭 Observabilidade

![Observability Schema](img/observability-schema.png)

Observabilidade é a capacidade de responder perguntas sobre o comportamento do sistema sem alterar o código. Em sistemas distribuídos com comunicação assíncrona, ela é indispensável.

### Pilar 1: Traces

Um trace registra o caminho completo de uma operação entre serviços. Um POST `/api/orders` gera spans em:

- `order-service` — handler HTTP, regra de negócio e banco
- `order-service` OutboxRelayWorker — polling e publicação no RabbitMQ
- `fraud-service` — consumidor RabbitMQ, análise antifraude e MongoDB
- `fraud-service` OutboxRelayWorker — publicação do resultado
- `order-service` — consumo do resultado, atualização do pedido e Inbox

### Pilar 2: Métricas

Medições numéricas agregadas ao longo do tempo.

**Métricas do order-service:**

| Métrica | Tipo | Descrição |
|---|---|---|
| `orders.created.total` | Counter | Pedidos criados, por faixa de valor |
| `orders.finalized.total` | Counter | Pedidos finalizados, por resultado |
| `orders.saga.duration.seconds` | Histogram | Duração fim a fim da saga |
| `orders.persist.duration.seconds` | Histogram | Latência de escrita no banco |
| `orders.outbox.published.total` | Counter | Publicações bem-sucedidas do Outbox |
| `orders.outbox.failed.total` | Counter | Falhas de publicação do Outbox |
| `orders.saga.timeouts.total` | Counter | Sagas expiradas |
| `orders.dlq.messages.received.total` | Counter | Mensagens de dead letter recebidas |

**Métricas do fraud-service:**

| Métrica | Tipo | Descrição |
|---|---|---|
| `fraud.orders.analyzed.total` | Counter | Pedidos analisados por status de fraude |
| `fraud.messages.received.total` | Counter | Mensagens RabbitMQ recebidas |
| `fraud.messages.duplicate.total` | Counter | Mensagens deduplicadas pelo Inbox |
| `fraud.analysis.duration.seconds` | Histogram | Latência do motor antifraude |
| `fraud.outbox.relay.duration` | Histogram | Duração do ciclo de relay |
| `fraud.mongodb.operation.duration` | Histogram | Latência das operações MongoDB |
| `fraud.processing.errors.total` | Counter | Erros de processamento por etapa |

### Pilar 3: Logs

Logs estruturados com correlação de trace. Cada linha carrega `trace_id` e `span_id`, permitindo filtrar logs de todos os serviços para uma única operação.

### Stack de observabilidade

```text
order-service (.NET)   -> OTEL Collector -> Jaeger     (traces)
fraud-service (Python) -> OTEL Collector -> Prometheus (metrics)
                       -> OTEL Collector -> Loki       (logs)
                                                |
                                             Grafana
```

### Por que usar OTEL Collector

Os serviços não exportam diretamente para Jaeger ou Prometheus. O Collector:

- **Desacopla** serviços do backend de observabilidade
- **Agrupa** spans e métricas para reduzir overhead
- **Enriquece** spans com atributos como `environment=development`
- **Oferece endpoint único** em `otel-collector:4317`

### Propagação de trace via RabbitMQ

HTTP propaga contexto automaticamente por headers; RabbitMQ não. Este projeto implementa W3C Trace Context em headers AMQP.

```csharp
Propagator.Inject(
    new PropagationContext(Activity.Current?.Context ?? default, Baggage.Current),
    properties,
    (props, key, value) => props.Headers![key] = Encoding.UTF8.GetBytes(value));
```

```python
normalized = {k: v.decode() if isinstance(v, bytes) else v for k, v in headers.items()}
return propagate.extract(normalized)
```

Assim, o span consumidor aparece como filho do span publicador no Jaeger, mesmo atravessando serviços e execução assíncrona.

---

## 🔍 Traces Distribuídos no Jaeger

### POST /api/orders — Criação do pedido

![POST Order Trace](img/example-observability-jaeger-order-service-POST.png)

O trace mostra a entrada HTTP, a regra `order.create`, a gravação `order.create.db` e a execução SQL Server. O span de banco confirma a gravação atômica do `Order` e do `OutboxMessage`.

### outbox.relay.cycle — A saga em movimento

![Outbox Relay Trace](img/example-observability-jaeger-order-service-outbox-relay-cycle.png)

Este é um dos traces mais importantes do sistema. Ele começa no `order-service` e cruza a fronteira para o `fraud-service` por propagação de trace via RabbitMQ. Todo o pipeline antifraude fica visível como spans filhos: consumo, verificação de Inbox, análise e persistência.

### fraud-service outbox.relay.cycle — Conclusão da saga

![Fraud Outbox Relay Trace](img/example-observability-jaeger-fraud-service-outbox-realy-cycle.png)

O resultado antifraude sai do Outbox do fraud-service, passa pelo RabbitMQ, chega ao consumidor do order-service e termina nas atualizações de banco. A conclusão da saga aparece em um único trace distribuído.

### GET /api/orders — Listagem de pedidos

![GET Orders Trace](img/example-observability-jaeger-order-service-GET.png)

Caminho simples de leitura: HTTP -> application layer -> consulta EF Core -> SQL Server. O span `order.list` é marcado com `db.system=mssql`, `db.operation=select` e `orders.count=N`.

### saga.timeout.check — Monitoramento em background

![Saga Timeout Trace](img/example-observability-jaeger-order-service-saga.timeout.check.png)

`SagaTimeoutWorker` roda a cada 60 segundos. Cada ciclo emite um trace curto. Quando há pedidos expirados, surgem spans filhos `saga.timeout.cancel`, um por pedido cancelado.

---

## 📊 Dashboards do Grafana

### Fraud Service Dashboard

**Before:**

![Fraud Service Before](img/grafana-dashboard-fraud-service-before.png)

O dashboard inicial cobre o essencial: taxa de recebimento de mensagens, throughput de análises por status, taxa de publicação do Outbox e latência P95 da análise antifraude e das operações MongoDB.

**After:**

![Fraud Service After](img/grafana-dashboard-fraud-service-after.png)

A versão evoluída adiciona quebras mais finas e contexto operacional: mensagens duplicadas, contadores de DLQ, erros por etapa, sucesso/falha por routing key e comparação entre latência do motor antifraude e transações MongoDB.

### Order Service — Business Dashboard

**Before:**

![Order Business Before](img/grafana-dashboard-order-service-before.png)

O baseline acompanha taxa de criação de pedidos, pedidos finalizados por status e quantidade atual de pedidos pendentes.

**After:**

![Order Business After](img/grafana-dashboard-order-service-after.png)

O dashboard melhorado adiciona histogramas de duração da saga, contador de timeout e gauge de pedidos pendentes com threshold visual.

### HTTP & Performance Dashboard

**Before:**

![HTTP Performance Before](img/grafana-dashboard-order-service-http-performace-before.png)

A versão inicial cobre taxa de requisições, latência P95 por endpoint, comparação P50/P95/P99 e taxa de erro.

**After:**

![HTTP Performance After](img/grafana-dashboard-order-service-http-performace-after.png)

A versão evoluída adiciona P99 por rota, painel dedicado de erro com thresholds, exclusão de redirects `3xx` dos cálculos e distribuição de tamanho de requisição.

### .NET Runtime Dashboard

**Before:**

![Runtime Before](img/grafana-dashboard-runtine-dotnet-before.png)

Os painéis iniciais mostram heap por geração de GC, taxa de exceções e coleta de GC por geração.

**After:**

![Runtime After](img/grafana-dashboard-runtine-dotnet-after.png)

A versão melhorada adiciona utilização do thread pool, histograma de pausa do GC e anotações para correlacionar picos de exceções com eventos de deploy.

---

## 🔔 Alertas no Grafana

![Error Rate Alert](img/grafana-error-rate-alert.png)

### Alerta de taxa de erro

Um alerta dispara quando a taxa de erro 5xx excede **5%** do total de requisições por pelo menos 1 minuto.

**Consulta do alerta (PromQL):**
```promql
rate(otel_http_server_request_duration_seconds_count{
    exported_job="order-service",
    http_response_status_code=~"5.."
}[5m])
/
rate(otel_http_server_request_duration_seconds_count{
    exported_job="order-service"
}[5m])
```

**Estados do alerta:**

- `Normal` — taxa de erro < 5%
- `Pending` — taxa de erro >= 5%, mas dentro da janela de confirmação
- `Firing` — taxa de erro >= 5% sustentada, com notificação enviada

O estado pending evita alertas instáveis quando uma requisição ruim causa um pico temporário.

---

## 📜 Logs Centralizados com Loki

![Logs Dashboard](img/grafana-dashboard-logs.png)

### Arquitetura Loki

![Loki Schema](img/loki-schema.png)

**Promtail** roda como sidecar, lê stdout/stderr dos containers via Docker socket, adiciona labels (`service`, `level`, `container`) e envia para o Loki.

**Loki** indexa logs apenas por labels, não pelo conteúdo completo. Isso reduz custo de armazenamento e memória quando comparado ao Elasticsearch.

**Grafana** fornece a interface de consulta com **LogQL**.

### Por que Loki em vez de Elasticsearch

| Aspecto | Loki | Elasticsearch |
|---|---|---|
| Estratégia de índice | Apenas labels | Conteúdo full-text |
| Custo de storage | Baixo | Alto |
| Modelo de consulta | LogQL | Elasticsearch DSL |
| Integração | Datasource nativo do Grafana | Exige Kibana ou plugin |
| Complexidade operacional | Baixa | Alta |
| Melhor uso | Microsserviços com stack Grafana | Busca full-text pesada |

Neste projeto, o principal caso de uso dos logs é correlação, como "mostrar todos os logs do `trace_id=abc-123`".

### Correlação trace-log

```text
Grafana: visualizar trace no Jaeger
    -> ver span com erro e trace_id=abc123def456
    -> clicar em "Logs for this trace"
    -> consulta Loki: {service="order-service"} |= "abc123def456"
    -> ver todas as linhas de log daquele request
```

Métricas alertam, traces localizam o problema, logs explicam o motivo.

---

## 🧪 Testes de Resiliência

### Cenário 1: ambos os serviços online

```json
POST /api/orders {"description": "test", "amount": 500.00}
-> {"status": "APPROVED", "createdAt": "...", "updatedAt": "..."}

POST /api/orders {"description": "test high", "amount": 10000.00}
-> {"status": "REJECTED", "createdAt": "...", "updatedAt": "..."}
```

Latência observada: ~200ms fim a fim.

### Cenário 2: fraud-service offline

```text
1. Parar o container fraud-service
2. POST /api/orders  ->  200 OK  (pedido criado, OutboxMessage = PENDING)
3. Iniciar o container fraud-service
4. GET /api/orders/{id}  ->  {"status": "APPROVED"}  (processado na recuperação)
```

**Resultado:** nenhuma mensagem perdida. Pedidos criados enquanto o fraud-service estava offline foram processados automaticamente quando ele voltou.

### Cenário 3: order-service offline após publicar

```text
1. POST /api/orders  ->  200 OK  (Order + OutboxMessage confirmados)
2. OutboxRelayWorker publica no RabbitMQ
3. Parar o container order-service
4. fraud-service processa a mensagem e publica resultado em order.result.queue
5. Resultado fica na fila
6. Iniciar o container order-service
7. OrderResultWorker consome o resultado em fila
8. GET /api/orders/{id}  ->  {"status": "REJECTED"}
```

**Resultado:** entrega eventual consistente. O resultado ficou preservado no RabbitMQ durante a indisponibilidade do order-service.

### Cenário 4: RabbitMQ offline

```text
1. Parar o container RabbitMQ
2. POST /api/orders  ->  200 OK  (Order no banco, OutboxMessage Status=PENDING)
3. OutboxRelayWorker registra: "RabbitMQ unavailable, retrying..."
4. Iniciar o container RabbitMQ
5. OutboxRelayWorker publica a mensagem pendente
6. fraud-service processa
7. GET /api/orders/{id}  ->  {"status": "APPROVED"}
```

**Antes do Outbox Pattern:** evento perdido permanentemente. Pedido preso em PENDING.  
**Depois do Outbox Pattern:** recuperação completa sem intervenção manual.

---

## ✨ Melhorias Implementadas

| Melhoria | Problema resolvido | Padrão/Ferramenta |
|---|---|---|
| **Transactional Outbox** | Perda de evento com broker indisponível | Outbox Pattern + OutboxRelayWorker |
| **Inbox + Idempotência** | Processamento duplicado de mensagens | Inbox Pattern + UNIQUE constraint |
| **Publisher Confirms** | Perda silenciosa de mensagens no broker | RabbitMQ ConfirmSelect |
| **ACK/NACK + DLQ** | Loops infinitos de retry | BasicNack(requeue:false) + DLQ |
| **Polly Retry** | Falhas transitórias de conexão | Pipeline com exponential backoff |
| **Lazy Connection** | Dependência do broker no startup | EnsureChannelIsOpen() |
| **Saga Pattern** | Coordenação de transações distribuídas | Coreografia orientada a eventos |
| **Saga Timeout** | Sagas órfãs presas para sempre | SagaTimeoutWorker + MarkAsTimedOut() |
| **API Gateway** | Endereços de serviço hard-coded | Traefik com roteamento por Docker labels |
| **Distributed Tracing** | Falta de visibilidade em fluxos assíncronos | OpenTelemetry + propagação W3C |
| **Custom Metrics** | Ausência de visibilidade de negócio | Meters, Counters, Histograms |
| **Grafana Dashboards** | Falta de visibilidade operacional | 4 dashboards cobrindo todas as camadas |
| **Alerting** | Resposta apenas reativa a incidentes | Alerta Grafana para taxa de erro > 5% |
| **Centralized Logs** | Logs efêmeros e isolados por container | Loki + Promtail + correlação por trace |
| **Infrastructure Topology** | Acoplamento por declaração de filas | Definições RabbitMQ pré-declaradas |

---

## 📚 Conceitos Aplicados

| Conceito | Descrição |
|---|---|
| **Microservices** | Cada serviço é implantável de forma independente, possui seu próprio banco e se comunica por mensagens |
| **Clean Architecture** | Camadas Domain, Application e Infrastructure com regras rígidas de dependência |
| **Event-Driven Architecture** | Serviços se comunicam apenas por eventos; sem HTTP síncrono entre serviços |
| **Transactional Outbox** | Persiste evento junto dos dados de negócio e publica depois via relay |
| **Inbox Pattern** | Registra IDs de eventos processados para detectar e ignorar duplicatas |
| **Idempotência** | Operações podem ser repetidas sem alterar o resultado final |
| **Saga (Coreografia)** | Transação distribuída coordenada por eventos, sem orquestrador central |
| **Consistência Eventual** | O sistema converge para estado consistente mesmo sem consistência imediata |
| **At-Least-Once Delivery** | RabbitMQ pode reenviar mensagens; consumidores precisam ser idempotentes |
| **Dead Letter Queue** | Mensagens com falha são preservadas para inspeção |
| **Publisher Confirms** | Broker confirma recebimento antes do publisher considerar a mensagem enviada |
| **Distributed Tracing** | Um trace atravessa múltiplos serviços e fronteiras assíncronas |
| **Polyglot Persistence** | SQL Server para dados relacionais/transacionais e MongoDB para dados documentais/flexíveis |
| **Resilience Patterns** | Retry com backoff exponencial, circuit-breaking e graceful degradation |
| **API Gateway** | Ponto único de entrada que oculta a topologia interna |
| **Observabilidade** | Traces + Métricas + Logs para entender o comportamento do sistema por sinais externos |

---

## 🔗 Referências e Materiais de Estudo

Este projeto foi desenvolvido com base em estudos, documentações oficiais, artigos e conteúdos da comunidade sobre arquitetura distribuída, microsserviços, observabilidade e padrões de integração.

### 📚 Materiais

- https://www.youtube.com/watch?v=Q5qZVWTQQOE
- https://www.youtube.com/watch?v=YNvH3QfG_UE&list=PLI2XdbZhEq4l-nnF4bfzsUBnnZXTtcV1D
- https://www.youtube.com/watch?v=0V7Lct-KfwI
- https://www.youtube.com/watch?v=9Nic_EhRCyo&t=1183s
- https://www.youtube.com/watch?v=ooJjxNsQnK4
- https://www.youtube.com/watch?v=JXeJUfBCg4U
- https://www.youtube.com/watch?v=8xFBQc1A4B8
- https://github.com/kgrzybek/modular-monolith-with-ddd
 

### 🤖 Ferramentas Utilizadas Durante o Desenvolvimento

- Claude AI  
  https://claude.ai/new

- ChatGPT  
  https://chatgpt.com/

---

## 🏁 Conclusão

Este projeto demonstra que construir sistemas distribuídos confiáveis exige muito mais do que escrever código que funciona. Os desafios reais aparecem nos espaços entre serviços: mensagens em trânsito, coordenação de transações entre fronteiras, recuperação de falhas parciais e entendimento do que acontece em processos e bancos diferentes.

Cada padrão implementado existe porque uma classe real de falhas de produção exige uma resposta:

- **Outbox Pattern** porque dual-write gera perda de dados sob falhas reais de rede
- **Inbox Pattern** porque entrega at-least-once é uma garantia fundamental do RabbitMQ
- **Saga Timeout** porque coordenação assíncrona sem prazo acumula recursos indefinidamente
- **Distributed Tracing** porque sistemas assíncronos orientados a mensagens são praticamente indepuráveis sem ele
- **Centralized Logs** porque stdout de containers é efêmero e correlação entre serviços exige armazenamento compartilhado

O investimento em observabilidade trouxe retorno imediato durante o desenvolvimento. Quando traces não conectavam pela fronteira do RabbitMQ, o Jaeger tornou a falha de propagação visível. Quando a consulta de timeout de saga atingia o índice errado, histogramas no Prometheus evidenciaram a regressão de latência antes de qualquer usuário perceber.

O sistema é um estudo prático do que "production-grade" significa no nível de infraestrutura e arquitetura: não por estar pronto para milhões de usuários, mas porque, quando algo falha, há ferramentas para entender o motivo, padrões para recuperar automaticamente e resiliência para continuar operando em modo degradado.

---

> Os materiais acima foram utilizados como apoio para estudo, validação de conceitos e implementação das soluções apresentadas neste projeto

---
<div align="center">

📬 Contato

Se você gostou do projeto? Tem alguma dica, feedback ou oportunidade? Vou gostar de conversar com você!

💼 LinkedIn: https://www.linkedin.com/in/rafaelviniciusbrambillaalves/

Feito para fins de **aprendizado e evolução técnica em Desenvolvimento de Software**

</div>
