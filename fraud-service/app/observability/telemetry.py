"""
Inicialização do OpenTelemetry para o fraud-service.
 
Ordem obrigatória de inicialização:
  1. setup_telemetry()   - configura TracerProvider e MeterProvider globais
  2. import fraud_metrics - usa get_meter() que já encontra o provider registrado
  3. instrument_app()    - instrumenta o FastAPI após o app ser criado
"""

import logging
import logging.config

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

SERVICE = "fraud-service"
VERSION = "1.0.0"

# Rotas de infraestrutura que não têm valor de negócio nos traces
_EXCLUDED_ROUTES  = ",".join([
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/health",
    "/metrics",
    "/favicon.ico"
])

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)

def setup_telemetry(otlp_endpoint: str) -> None:
    """
    Inicializa o SDK do OpenTelemetry: traces, métricas e propagação W3C.
 
    DEVE ser chamado como primeira coisa em main.py, antes de qualquer import
    que use get_meter() ou get_tracer() para criar instrumentos.
 
    Args:
        otlp_endpoint: URL do OTEL Collector, ex: "http://otel-collector:4317"
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

    # Logging estruturado com trace_id / span_id injetados
    _configure_logging()


    logger.info(
        "OpenTelemetry initialized | service=%s | endpoint=%s",
        SERVICE,
        otlp_endpoint
    )


def _configure_logging() -> None:
    """
    Configura o logging do Python para:
      - Formato JSON-like com trace_id e span_id injetados automaticamente.
      - Nível INFO por padrão; DEBUG para bibliotecas internas desativado.
      - Handler de console estruturado compatível com Loki
 
    O OTelTraceContextFilter injeta trace_id e span_id em cada LogRecord,
    permitindo correlacionar logs com traces no Grafana sem nenhuma mudança
    nos sites de chamada (logger.info, logger.error, etc.).
    """
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "otel_trace": {
                "()": _OtelTraceContextFilter,
            },
        },
        "formatters": {
            "structured": {
                # Formato compatível com Loki structured metadata.
                # trace_id e span_id são injetados pelo filtro acima.
                "format": (
                    "%(asctime)s "
                    "level=%(levelname)s "
                    "logger=%(name)s "
                    "trace_id=%(otel_trace_id)s "
                    "span_id=%(otel_span_id)s "
                    "| %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "filters": ["otel_trace"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
        # Silencia bibliotecas que poluem muito os logs.
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "motor":          {"level": "WARNING"},
            "pymongo":        {"level": "WARNING"},
            "aio_pika":       {"level": "WARNING"},
            "aiormq":         {"level": "WARNING"},
        },
    })


class _OtelTraceContextFilter(logging.Filter):
    """
    Injeta trace_id e span_id do span ativo em cada LogRecord.
 
    Se não há span ativo (ex: log de startup), usa "0" como valor
    para manter o formato do log consistente e evitar KeyError no formatter.
 
    Resultado: cada linha de log contém os IDs necessários para correlação
    no Grafana -> Explore -> Logs -> "Show in traces".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.is_valid:
            record.otel_trace_id = format(ctx.trace_id, "032x")
            record.otel_span_id = format(ctx.span_id, "016x")
        else:
            record.otel_trace_id = "0" * 32
            record.otel_span_id = "0" * 16


def instrument_app(app) -> None:
    """
    Instrumenta o FastAPI automaticamente após o app ser criado.
 
    Separado de setup_telemetry() porque o app precisa existir primeiro.
    Captura spans para cada request HTTP com método, rota e status code.
    """

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls = _EXCLUDED_ROUTES
    )

