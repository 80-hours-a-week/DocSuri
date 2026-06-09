"""Observability primitives (AGENTS.md §4.6).

Single entry point: ``setup_observability(app)`` wires OTel tracing,
HTTPX/Celery/Redis auto-instrumentation, and JSON structured logging into
the FastAPI app. Trace backend is OTLP-over-HTTP; when
``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset the SDK falls back to a no-op
exporter, keeping local dev quiet.
"""

from app.crosscutting.observability.logging import configure_logging
from app.crosscutting.observability.tracing import setup_observability

__all__ = ["configure_logging", "setup_observability"]
