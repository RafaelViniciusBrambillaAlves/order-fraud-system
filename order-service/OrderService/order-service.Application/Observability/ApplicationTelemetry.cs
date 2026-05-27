using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using System.Diagnostics.Metrics;
using order_service.Application.Services;

namespace order_service.Application.Observability
{
    /// <summary>
    /// Ponto central de instrumentacao do order-service.
    /// Todos os ActivitySource, Meter, Counter e Histogram vivem aqui
    ///
    /// Regras de nomenclatura seguidas:
    ///   - Contadores   -> {domínio}.{entidade}.{ação}.total
    ///   - Histogramas  -> {domínio}.{entidade}.{ação}.duration.seconds
    ///   - Gauges       -> {domínio}.{entidade}.{estado}.current
    /// </summary>
    public static class ApplicationTelemetry
    {
        public const string ServiceName = "order-service";
        public const string ServiceVersion = "1.0.0";

        public static readonly ActivitySource ActivitySource =
            new(ServiceName, ServiceVersion);

        private static readonly Meter Meter =
            new(ServiceName, ServiceVersion);


        // CONTADORES DE NEGOCIO

        // Conta pedidos criado com sucesso
        public static readonly Counter<long> OrdersCreated = 
            Meter.CreateCounter<long>(
                name: "orders.created.total",
                unit: "{orders}",
                description: "Total numbers of orders created successfully");

        // Conta pedidos por status final (APPROVED, REJECTED, TIMEOUT)
        public static readonly Counter<long> OrdersFinalized = 
            Meter.CreateCounter<long>(
                name: "orders.finalized.total",
                unit: "{orders}",
                description: "Total orders finalized, tagged by result");

        // Conta error por operacao 
        public static readonly Counter<long> OperationErrors = 
            Meter.CreateCounter<long>(
                name: "orders.operation.errors.total",
                unit: "{errors}",
                description: "Total errors per operation type");


        // HISTOGRAMAS DE NEGOCIO

        // Duracao total do ciclo de uma saga
        public static readonly Histogram<double> SagaDuration = 
            Meter.CreateHistogram<double>(
                name: "orders.saga.duration.seconds",
                unit: "s",
                description: "Duration of the order processing saga");

        // Latencia de persistencia atomica (order + outbox) no banco 
        public static readonly Histogram<double> OrderPersistenceDuration = 
            Meter.CreateHistogram<double>(
                name: "orders.persist.duration.seconds",
                unit: "s",
                description: "Duration of order persistence (order + outbox)");

        
        // GAUGE DE NEGOCIO

        // Delegate que o gauge vai invocar periodicamente para obter o valor real.
        // Inicializado com 0 e substituído em ApplicationModule via SetPendingOrdersProvider().
        private static Func<int> _pendingOrdersProvider = () => 0;

        /// <summary>
        /// Registra o delegate que retorna a contagem real de pedidos PENDING.
        /// Deve ser chamado uma vez durante o startup, após o DI estar configurado.
        ///
        /// Exemplo em ApplicationModule:
        ///   ApplicationTelemetry.SetPendingOrdersProvider(() =>
        ///       scope.ServiceProvider
        ///           .GetRequiredService&lt;IOrderRepository&gt;()
        ///           .CountPendingAsync().GetAwaiter().GetResult());
        /// </summary>
        public static void SetPendingOrdersProvider(Func<int> provider)
            => _pendingOrdersProvider = provider ?? throw new ArgumentNullException(nameof(provider));

        public static readonly ObservableGauge<int> OrdersPending;
    
        static ApplicationTelemetry()
        {
            OrdersPending = Meter.CreateObservableGauge(
                name: "orders.pending.current",
                observeValue: () => new Measurement<int>(_pendingOrdersProvider()),
                unit: "{orders}",
                description: "Orders awaiting results from anti-fraud analysis (status PENDING_FRAUD_CHECK)");
        }


        // METRICAS DO OUTBOX RELAY WORKER

        // OutboxRelayWorker - mensagens publicadas com sucesso
        public static readonly Counter<long> OutboxMessagesPublished = 
            Meter.CreateCounter<long>(
                name: "orders.outbox.published.total",
                unit: "{messages}",
                description: "Total outbox messages published successfully");

        // OutboxRelayWorker: mensagens que falharam na publicacao
        public static readonly Counter<long> OutboxMessagesFailed = 
            Meter.CreateCounter<long>(
                name: "orders.outbox.failed.total",
                unit: "{messages}",
                description: "Total outbox messages failed to publish");

        // OutboxRelayWorker: tempo de cada ciclo do relay
        public static readonly Histogram<double> OutboxRelayDuration = 
            Meter.CreateHistogram<double>(
                name: "orders.outbox.relay.duration.seconds",
                unit: "s",
                description: "Duration of each outbox relay cycle");

        
        // METRICAS DO SAGA TIMEOUT WORKER

        // SagaTimeoutWorker: sagas que expiraram
        public static readonly Counter<long> SagaTimeouts = 
            Meter.CreateCounter<long>(
                name: "orders.saga.timeouts.total",
                unit: "{sagas}",
                description: "Total number of sagas that expired");

        // SagaTimeoutWorker: tempo de cada ciclo de verificação
        public static readonly Histogram<double> SagaTimeoutCheckDuration = 
            Meter.CreateHistogram<double>(
                name: "orders.saga.timeout.check.duration.seconds",
                unit: "s",
                description: "Duration of each saga timeout check cycle");

        
        // METRICAS DLQ

        // DlqWorker: mensagens mortas recebidas
        public static readonly Counter<long> DlqMessagesReceived = 
            Meter.CreateCounter<long>(
                name: "orders.dlq.messages.received.total",
                unit: "{messages}",
                description: "Total dead-letter messages received for processing");
        
        // Duracao de processamento de cada mensagem DLQ
        public static readonly Histogram<double> DlqProcessingDuration =
            Meter.CreateHistogram<double>(
                name: "orders.dlq.processing.duration.seconds",
                unit: "s",
                description: "Duration of each message in DLQ");

        
        // METRICAS DO PUBLISHER / SUBSCRIBER
        
        // Latencia de cada publicao no RabbtiMQ
        public static readonly Histogram<double> PublisherDuration = 
            Meter.CreateHistogram<double>(
                name: "orders.publisher.duration.seconds",
                unit: "s",
                description: "Duration of publisher in RabbitMQ");
    }
}
