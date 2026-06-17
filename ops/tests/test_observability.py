from __future__ import annotations

from docsuri_ops.adapters.local import InMemoryEventStore
from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import TelemetryEvent
from docsuri_ops.observability import ObservabilityHub, redact


def test_redact_removes_sensitive_keys_and_emails() -> None:
    payload = {
        "email": "researcher@example.com",
        "nested": {"token": "secret-token", "message": "contact a@b.com"},
    }

    assert redact(payload) == {
        "email": "[REDACTED]",
        "nested": {"token": "[REDACTED]", "message": "contact [REDACTED_EMAIL]"},
    }


def test_observability_log_preserves_request_id_and_redacts() -> None:
    store = InMemoryEventStore()
    hub = ObservabilityHub(store)

    hub.emit_log({"eventId": "log-1", "requestId": "req-1", "password": "nope"})

    assert len(store.events) == 1
    event = store.events[0]
    assert event.request_id == "req-1"
    assert event.payload["password"] == "[REDACTED]"


def test_audit_is_append_only() -> None:
    store = InMemoryEventStore()
    hub = ObservabilityHub(store)

    hub.audit_append({"eventId": "audit-1", "action": "authorize", "user_id": "u1"})
    hub.audit_append({"eventId": "audit-2", "action": "authorize", "user_id": "u1"})

    assert [event["eventId"] for event in store.audit_events] == ["audit-1", "audit-2"]
    assert all(event["user_id"] == "[REDACTED]" for event in store.audit_events)


def test_duplicate_event_id_is_idempotent() -> None:
    store = InMemoryEventStore()
    event = TelemetryEvent(event_id="same", kind=SignalKind.METRIC, name="x", value=1.0)

    assert store.append(event)
    assert not store.append(event)
    assert len(store.events) == 1
