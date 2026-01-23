"""OpenTelemetry setup and configuration."""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from ..storage.db_manager import get_db_manager
from .otel_exporter import SqliteSpanExporter


def setup_opentelemetry():
    """Initialize OpenTelemetry SDK with SQLite exporter and optional OTLP exporter."""
    # Create resource
    resource = Resource.create({
        "service.name": "tracelens",
        "service.version": "0.1.0",
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Add SQLite exporter (always enabled)
    db_path = os.getenv("DATABASE_PATH", "./tracelens.db")
    sqlite_exporter = SqliteSpanExporter(db_path)
    provider.add_span_processor(BatchSpanProcessor(sqlite_exporter))
    
    # Add OTLP exporter if endpoint is configured (optional)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except ImportError:
            # OTLP exporter not installed, skip silently
            pass
    
    # Also add console exporter for debugging (optional)
    if os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true":
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Instrument HTTP clients (for LLM API calls)
    HTTPXClientInstrumentor().instrument()
    
    return provider


def get_tracer(name: str = "tracelens"):
    """Get a tracer instance."""
    return trace.get_tracer(name)


# Context propagator for async operations
propagator = TraceContextTextMapPropagator()


def inject_context(carrier: dict):
    """Inject trace context into a carrier dict."""
    propagator.inject(carrier)


def extract_context(carrier: dict):
    """Extract trace context from a carrier dict."""
    return propagator.extract(carrier)
