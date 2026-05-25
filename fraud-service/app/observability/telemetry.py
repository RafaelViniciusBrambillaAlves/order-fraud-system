from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
# from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

import logging

logger = logging.getLogger(__name__)

SERVICE = "fraud-service"
VERSION = "1.0.0"

# tracer: trace.Tracer = trace.get_tracer(SERVICE, VERSION)
# meter: metrics.Meter = metrics.get_meter(SERVICE, VERSION)




# Rotas de infraestrutura que não têm valor de negócio nos traces
_EXCLUDED_ROUTES  = frozenset([
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/health",
    "/metrics",
    "/favicon.ico"
])

def setup_telemetry(otlp_endpoint: str) -> None:
    """
    Inicializa o SDK do OpenTelemetry.
    """
    resource = Resource.create({
        SERVICE_NAME: SERVICE,
        SERVICE_VERSION: VERSION
    }) 

    # Traces 
    tracer_provider = TracerProvider(resource = resource)

    span_exporter = OTLPSpanExporter(
        endpoint = otlp_endpoint, 
        insecure = True
    )
    
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metrics_exporter = OTLPMetricExporter(
        endpoint = otlp_endpoint,
        insecure = True,
    )

    metrics_reader = PeriodicExportingMetricReader(
        metrics_exporter, 
        export_interval_millis = 10_000
    )
    
    meter_provider = MeterProvider(
        resource = resource,
        metric_readers = [metrics_reader]
    )

    metrics.set_meter_provider(meter_provider)

    # Propagação
    set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])
    )

    # Database Instrumentation

    PymongoInstrumentor().instrument()

    logger.info(
        "OpenTelemetry initialized | service=%s | endpoint=%s",
        SERVICE,
        otlp_endpoint
    )



def instrument_app(app) -> None:
    """
    Instrumenta o FastAPI automaticamente.
    Captura spans para cada request HTTP — método, rota, status code.
    Separado do setup_telemetry para poder ser chamado após criar o app.
    """

    # def _should_exclude(scope: dict) -> bool:
    #     path = scope.get("path", "")
    #     return path in _EXCLUDED_ROUTES or path.startswith("/docs")
    
    excluded_urls = ",".join(_EXCLUDED_ROUTES)

    FastAPIInstrumentor.instrument_app(
        app,
        # filter_func = lambda scope, _receive: not _should_exclude(scope)
        excluded_urls = excluded_urls
    )

tracer = trace.get_tracer(__name__)