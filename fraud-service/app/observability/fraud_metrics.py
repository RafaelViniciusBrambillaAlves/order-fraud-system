"""
Metricas de negócio e infraestrutura do fraud-service.

"""

from opentelemetry import metrics

_meter = metrics.get_meter("fraud-service", "1.0.0")


# METRICAS DE NEGOCIO

orders_analyzed_total = _meter.create_counter(
    name="fraud.orders.analyzed.total",
    unit="{orders}",
    description="Total analyzed orders"
)
"""
Tags esperadas:
  fraud_status: "approved" | "rejected"  (minúsculo, consistente com FraudStatus.value)
"""


fraud_decisions_total = _meter.create_counter(
    name="fraud.decisions.total",
    unit="{decisions}",
    description="Fraud decisions by status"
)
"""
Tags esperadas:
  decision: "approved" | "rejected"
 
Incrementado em analyze_order.py junto com orders_analyzed_total.
"""

# METRICAS DE MENSAGERIA

# Mensagem recebida do RabbitMQ
messages_received_total = _meter.create_counter(
    name = "fraud.messages.received.total",
    unit = "{messages}",
    description = "Total RabbitMQ messages received by the fraud-service"
)

# Mensagens duplicadas detectadas pelo inbox 
duplicate_messages_total = _meter.create_counter(
    name = "fraud.messages.duplicate.total",
    unit = "{messages}",
    description = "Total duplicate messages skipped via inbox idempotency"
)

# Total de mensagens dead-letter recebidas no fraud-service
dlq_messages_received_total = _meter.create_counter(
    name = "fraud.dlq.messages.received.total",
    unit = "{messages}",
    description = "Total dead letter messages received in the fraud-service"
)

# Mensagens de outbox publicadas com sucesso no RabbitMQ
outbox_messages_published_total = _meter.create_counter(
    name="fraud.outbox.messages.published.total",
    unit="{messages}",
    description="Outbox messages successfully published"
)

# Mensagens de outbox que falharam na publicação
outbox_messages_failed_total = _meter.create_counter(
    name="fraud.outbox.messages.failed.total",
    unit="{messages}",
    description="Outbox messages failed to publish"
)


# METRICAS DE ERRO

# Mensagens que falharam no processamento
processing_errors_total  = _meter.create_counter(
    name = "fraud.processing.errors.total",
    unit = "{errors}",
    description = "Total messages processing errors in the fraud-service"
)
"""Tags esperadas: stage — "consumer" | "handler" | "outbox_relay_publish" | "dlq" """


# HISTOGRAMAS DE LATÊNCIA

# Latencia total do processamento de uma mensagem 
message_processing_duration = _meter.create_histogram(
    name = "fraud.message.processing.duration.seconds",
    unit = "s",
    description = "Total processing latency for each message in the fraud-service"
)

# Latencia so da analise de fraude
analysis_duration = _meter.create_histogram(
    name = "fraud.analysis.duration.seconds",
    unit = "s",
    description = "Latency of the fraud analysis step in the fraud-service"
)

# Tempo de cada ciclo do OutboxRelayWorker
outbox_relay_duration = _meter.create_histogram(
    name = "fraud.outbox.relay.duration.seconds",
    unit = "s",
    description = "Duration of each OutboxRelayWorker processing cycle",
)

# Latência de publicação individual no RabbitMQ
publisher_duration = _meter.create_histogram(
    name = "fraud.publisher.duration.seconds",
    unit = "s",
    description = "RabbitMQ publish latency"
)

# Duração de operações MongoDB
mongodb_operation_duration = _meter.create_histogram(
    name = "fraud.mongodb.operation.duration",
    unit = "s",
    description = "MongoDB operation duration"
)

# Duração de processamento de cada mensagem na DLQ
dlq_processing_duration = _meter.create_histogram(
    name = "fraud.dlq.processing.duration.seconds",
    unit = "s",
    description = "Processing time for each message in DLQ"
)


# GAUGES DE INFRAESTRUTURA

rabbitmq_connection_status = _meter.create_up_down_counter(
    name = "fraud.rabbitmq.connection.status",
    unit = "{connection}",
    description = "RabbitMQ connection status (1 = up, -1 = down)"
)
"""
Incrementar com +1 quando conectar, -1 quando desconectar.
Usado em alertas: fraud_rabbitmq_connection_status < 1 → dispara alerta.
Deve ser atualizado no startup.py após connect_robust() e no handler de reconexão.
"""

mongodb_connection_status = _meter.create_up_down_counter(
    name = "fraud.mongodb.connection.status",
    unit = "{connection}",
    description = "MongoDB connection status (1 = up, -1 = down)"
)

outbox_pending_gauge = _meter.create_observable_gauge(
    name = "fraud.outbox.pending.current",
    unit = "{messages}",
    description = "Outbox messages awaiting publication (status PENDING)",
    callbacks = []
)

def register_outbox_pending_callback(callback) -> None:
    """
    Registra o callable que retorna a contagem atual de mensagens PENDING no outbox.
 
    Deve ser chamado uma vez no startup.py após o repositório MongoDB estar pronto.
    O SDK chama o callback periodicamente (a cada export_interval_millis).
 
    Args:
        callback: callable sem argumentos que retorna int
    """
    global outbox_pending_gauge

    outbox_pending_gauge = _meter.create_observable_gauge(
        name = "fraud.outbox.pending.current",
        unit = "{messages}",
        description = "Outbox messages awaiting publication (status PENDING)",
        callbacks = [lambda _options: [metrics.Observation(callback())]]
    ) 




