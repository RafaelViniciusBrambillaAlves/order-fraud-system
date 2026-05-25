from opentelemetry import metrics


_meter = metrics.get_meter("fraud-service", "1.0.0")

# BUSINESS METRICS

orders_analyzed_total = _meter.create_counter(
    name="fraud.orders.analyzed.total",
    unit="{orders}",
    description="Total analyzed orders"
)

fraud_decisions_total = _meter.create_counter(
    name="fraud.decisions.total",
    unit="{decisions}",
    description="Fraud decisions by status"
)


# MESSAGING METRICS

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

dlq_messages_received_total = _meter.create_counter(
    name = "fraud.dlq.messages.received.total",
    unit = "{messages}",
    description = "Total dead letter messages received in the fraud-service"
)

outbox_messages_published_total = _meter.create_counter(
    name="fraud.outbox.messages.published",
    unit="{message}",
    description="Outbox messages successfully published"
)

outbox_messages_failed_total = _meter.create_counter(
    name="fraud.outbox.messages.failed",
    unit="{message}",
    description="Outbox messages failed to publish"
)


# ERROR METRICS

# Mensagens que falharam no processamento
processing_errors_total  = _meter.create_counter(
    name = "fraud.processing.errors.total",
    unit = "{errors}",
    description = "Total messages processing errors in the fraud-service"
)


# LATENCY METRICS

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
    name = "fraud.outbox.relay.duration",
    unit = "s",
    description = "Duration of each OutboxRelayWorker processing cycle",
)

publisher_duration = _meter.create_histogram(
    name="fraud.publisher.duration",
    unit="s",
    description="RabbitMQ publish latency"
)

mongodb_operation_duration = _meter.create_histogram(
    name="fraud.mongodb.operation.duration",
    unit="s",
    description="MongoDB operation duration"
)


# INFRASTRUCTURE METRICS

rabbitmq_connection_status = _meter.create_up_down_counter(
    name="fraud.rabbitmq.connection.status",
    unit="{connection}",
    description="RabbitMQ connection status (1=up, 0=down)"
)

mongodb_connection_status = _meter.create_up_down_counter(
    name="fraud.mongodb.connection.status",
    unit="{connection}",
    description="MongoDB connection status (1=up, 0=down)"
)