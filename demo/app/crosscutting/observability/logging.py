"""Structured logging — JSON by default, console for local dev.

AGENTS.md §4.6 ops convention requires structured logs so Loki / CloudWatch
can index per-feature p95 + error rate. The JSON shape carries the active
OTel ``trace_id`` / ``span_id`` so a log line in CloudWatch links to the
matching trace in Tempo (or whichever backend wins the §4.6 selection).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from opentelemetry import trace
from pythonjsonlogger import jsonlogger


class _TraceContextFilter(logging.Filter):
    """Inject the active span's trace_id / span_id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        return True


class _JsonFormatter(jsonlogger.JsonFormatter):
    """Stamp service + env into every record so multi-service log streams demux."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("service", os.getenv("OTEL_SERVICE_NAME", "docsuri-api"))
        log_record.setdefault("env", os.getenv("DEPLOY_ENV", "dev"))
        log_record.setdefault("level", record.levelname)


def configure_logging() -> None:
    """Install the JSON/console handler. Idempotent."""
    fmt = os.getenv("LOG_FORMAT", "json").lower()
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_TraceContextFilter())

    if fmt == "json":
        formatter: logging.Formatter = _JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
            " %(trace_id)s %(span_id)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [%(trace_id)s] %(message)s"
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn defaults are noisy; demote access log to INFO and let our
    # structured handler take over its formatting.
    for noisy in ("uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(noisy)
        lg.handlers = []
        lg.propagate = True
