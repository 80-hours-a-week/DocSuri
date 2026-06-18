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


def test_dedup_window_is_bounded_lru(monkeypatch) -> None:
    """_seen is a bounded LRU — it never exceeds the window and only the OLDEST keys are evicted,
    so recent duplicates still dedup. Guards the per-request-metric memory leak. (US-R4)"""
    import docsuri_ops.adapters.local as local

    monkeypatch.setattr(local, "_MAX_SEEN", 3)
    store = InMemoryEventStore()

    def ev(eid: str) -> TelemetryEvent:
        return TelemetryEvent(event_id=eid, kind=SignalKind.METRIC, name="m", value=1.0)

    for eid in ["a", "b", "c", "d", "e"]:  # 5 unique ids > window of 3
        assert store.append(ev(eid)) is True
    assert len(store._seen) <= 3  # bounded — does NOT grow with unique events
    assert store.append(ev("e")) is False  # recent → still deduped
    assert store.append(ev("a")) is True  # oldest was evicted → re-accepted (bounded, not a leak)


def test_cloudwatch_append_is_nonblocking_and_flush_ships(monkeypatch) -> None:
    """append() enqueues (no boto3 in the caller's thread) and the background worker ships on
    flush() — so the async gateway never blocks the event loop on PutMetricData. (US-R4)"""
    from docsuri_ops.adapters.cloudwatch import CloudWatchEventStore

    shipped: list[str] = []
    monkeypatch.setattr(
        CloudWatchEventStore, "_put_metric", lambda self, event: shipped.append(event.name or "")
    )
    store = CloudWatchEventStore(namespace="Test")
    try:
        assert store.append(
            TelemetryEvent(event_id="m1", kind=SignalKind.METRIC, name="x", value=1.0)
        ) is True
        store.flush()  # block until the worker drains the queue
        assert shipped == ["x"]
    finally:
        store.close()
