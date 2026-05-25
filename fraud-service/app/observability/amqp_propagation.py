from typing import Dict, Any, Optional
from opentelemetry import propagate, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_propagator = TraceContextTextMapPropagator()

def extract_trace_context(headers: Optional[Dict[str, Any]]) -> context.Context:
    """
    Extrai o contexto de trace dos headers da mensagem.
    """

    if not headers:
        return context.get_current()
    
    # Normaliza: converte bytes - str para o propagador conseguir ler
    normalized: Dict[str, str] = {}
    for key, value in headers.items():
        if isinstance(value, bytes):
            normalized[key] = value.decode("utf-8")
        elif isinstance(value, str):
            normalized[key] = value
    
    return propagate.extract(normalized)


def inject_trace_context(header: Dict[str, Any]) -> None:
    """
    Injeta o contexto de trace nos headers da mensagem.
    """
    propagate.inject(header)
