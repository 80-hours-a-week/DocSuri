"""OTel SDK setup + auto-instrumentation (AGENTS.md §4.6).

We register a single ``TracerProvider`` and let the FastAPI / HTTPX / Celery
/ Redis instrumentors attach. Backend selection (Tempo vs Honeycomb vs
Datadog) is deferred — until ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, the
provider runs without an exporter, so the SDK overhead stays at trace-only
sampling and produces no network traffic.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_INSTALLED = False


def _build_resource() -> Resource:
    attrs = {
        "service.name": os.getenv("OTEL_SERVICE_NAME", "docsuri-api"),
    }
    extra = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
    for piece in extra.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            attrs[k.strip()] = v.strip()
    return Resource.create(attrs)


def setup_observability(app: FastAPI) -> None:
    """Install OTel tracing + auto-instrumentation. Idempotent.

    ``configure_logging()`` should be called *first* so trace context is
    available to log records emitted during instrumentation.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    provider = TracerProvider(resource=_build_resource())
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    else:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT unset — running tracer without exporter")

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()

    _INSTALLED = True
