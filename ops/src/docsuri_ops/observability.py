from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import TelemetryEvent

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "set-cookie",
    "email",
    "user_id",
    "userId",
    "owner",
}
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key) in _SENSITIVE_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    return value


@dataclass(slots=True)
class Span:
    name: str
    context: Any
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None

    def finish(self) -> None:
        self.ended_at = datetime.now(UTC)


class ObservabilityHub:
    def __init__(self, event_store) -> None:
        self._event_store = event_store

    def emit_metric(self, name: str, value: float, tags) -> None:
        safe_tags = {str(key): str(value) for key, value in redact(dict(tags)).items()}
        self._event_store.append(
            TelemetryEvent(
                event_id=f"metric:{name}:{uuid4().hex}",
                kind=SignalKind.METRIC,
                name=name,
                value=float(value),
                tags=safe_tags,
            )
        )

    def emit_log(self, entry: Any) -> None:
        payload = redact(dict(entry)) if isinstance(entry, dict) else {"message": redact(entry)}
        request_id = payload.get("requestId") or payload.get("request_id")
        self._event_store.append(
            TelemetryEvent(
                event_id=str(payload.get("eventId") or f"log:{uuid4().hex}"),
                kind=SignalKind.LOG,
                request_id=str(request_id) if request_id else None,
                payload=payload,
            )
        )

    def start_span(self, name: str, context: Any) -> Span:
        span = Span(name=name, context=redact(context))
        self._event_store.append(
            TelemetryEvent(
                event_id=f"span:{name}:{uuid4().hex}",
                kind=SignalKind.METRIC,
                name=f"span.{name}.started",
                value=1.0,
            )
        )
        return span

    def audit_append(self, event: Any) -> None:
        payload = redact(dict(event)) if isinstance(event, dict) else {"event": redact(event)}
        append = getattr(self._event_store, "append_audit", None)
        if append is not None:
            append(payload)
        self._event_store.append(
            TelemetryEvent(
                event_id=str(payload.get("eventId") or f"audit:{uuid4().hex}"),
                kind=SignalKind.AUDIT,
                request_id=payload.get("requestId") or payload.get("request_id"),
                payload=payload,
            )
        )


@contextmanager
def observed_span(hub: ObservabilityHub, name: str, context: Any):
    span = hub.start_span(name, context)
    try:
        yield span
    finally:
        span.finish()
