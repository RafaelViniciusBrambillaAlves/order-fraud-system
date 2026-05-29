import logging
import json
import sys
from datetime import datetime, timezone
from opentelemetry import trace


class JsonFormatter(logging.Formatter):
    """
    Emite cada linha de log como um objeto JSON com campos
    que o Promtail consegue parsear e o Loki indexar como labels.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Contexto de trace do OpenTelemetry
        span = trace.get_current_span()
        ctx = span.get_span_context if span else None

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "levelname": record.levelname,
            "message": self.formatMessage(record),
            "logger": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "service": "fraud-service",
        }

        # Injeta traceId e spanId se existirem - permite correlação no Grafana
        if ctx and ctx.is_valid:
            log_entry["otelTraceID"] = format(ctx.trace_id, "032x")
            log_entry["otelSpanID"] = format(ctx.span_id, "016x")

        # Inclui exceção formatada se houver
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Campos extras adicionados via logger.info("msg", extra={"order_id": ...})
        for key, value in record.__dict__.item():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            ):
                log_entry[key] = value
        
        return json.dumps(log_entry, default = str, ensure_ascii = False)
    
def setup_logging(level: str = "INFO") -> None:
    """
    Configura o logging global da aplicação para emitir JSON no stdout.
    Deve ser chamado antes de qualquer import que use logging.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter)
    root.addHandler(handler)

    # Silencia loggers muito verbosos da infra
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING) 
    logging.getLogger("aiormq").setLevel(logging.WARNING)       