from __future__ import annotations

from datetime import timedelta

from docsuri_ops.adapters.local import CapturingAlertPublisher, InMemoryIncidentStore
from docsuri_ops.dashboard import OpsDashboardService
from docsuri_ops.domain.enums import IncidentClass, Severity
from docsuri_ops.domain.models import (
    AlertRecord,
    ClassifiedIncidentRecord,
    DashboardWindow,
    IncidentCandidate,
    utc_now,
)
from docsuri_ops.incidents import AiIncidentDetectorSuite, IncidentEventPublisher


def test_incident_suite_classifies_three_res11_classes() -> None:
    suite = AiIncidentDetectorSuite()

    records = [
        suite.classify(
            IncidentCandidate(
                incident_class=IncidentClass.COST_EXPLOSION,
                severity=Severity.WARNING,
                request_id="req-cost",
                reason="cost",
                signal_id="sig-cost",
            )
        ),
        suite.classify(
            IncidentCandidate(
                incident_class=IncidentClass.HALLUCINATION,
                severity=Severity.CRITICAL,
                request_id="req-hallucination",
                reason="hallucination",
                signal_id="sig-hallucination",
            )
        ),
        suite.classify(
            IncidentCandidate(
                incident_class=IncidentClass.PARTIAL_RESULT,
                severity=Severity.WARNING,
                request_id="req-partial",
                reason="partial",
                signal_id="sig-partial",
            )
        ),
    ]

    assert [record.incident_class.value for record in records] == ["a", "b", "c"]


def test_incident_publisher_emits_shared_events_and_suppresses_duplicates() -> None:
    store = InMemoryIncidentStore()
    sink = CapturingAlertPublisher()
    publisher = IncidentEventPublisher(store, sink)
    candidate = IncidentCandidate(
        incident_class=IncidentClass.COST_EXPLOSION,
        severity=Severity.WARNING,
        request_id="req-cost",
        reason="monthly cost threshold exceeded",
        signal_id="sig-cost",
    )

    assert publisher.publish_candidate(candidate)
    assert not publisher.publish_candidate(candidate)

    assert len(store.incidents) == 1
    assert len(store.alerts) == 1
    assert len(sink.incidents) == 1
    assert sink.incidents[0].class_.value == "a"
    assert len(sink.alerts) == 1


def test_dashboard_aggregates_windowed_incidents_and_alerts() -> None:
    store = InMemoryIncidentStore()
    now = utc_now()
    store.append_incident(
        ClassifiedIncidentRecord(
            incident_class=IncidentClass.HALLUCINATION,
            severity=Severity.CRITICAL,
            request_id="req-1",
            reason="grounding",
            timestamp=now,
        )
    )
    store.append_alert(
        AlertRecord(
            severity=Severity.CRITICAL,
            request_id="req-1",
            reason="grounding",
            timestamp=now,
        )
    )
    dashboard = OpsDashboardService(store)

    view = dashboard.get_dashboard(
        DashboardWindow(now - timedelta(minutes=1), now + timedelta(minutes=1))
    )

    assert view.incident_count == 1
    assert view.alert_count == 1
    assert dashboard.summarize_by_class(view.window) == {"a": 0, "b": 1, "c": 0}
