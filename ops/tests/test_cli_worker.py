from __future__ import annotations

import json

from docsuri_ops.adapters.local import (
    CapturingAlertPublisher,
    InMemoryIncidentStore,
    InMemoryTelemetrySource,
)
from docsuri_ops.cli import main
from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import TelemetryEvent
from docsuri_ops.incidents import AiIncidentDetectorSuite, IncidentEventPublisher
from docsuri_ops.worker import run_once, run_polling_loop


def test_worker_run_once_publishes_detected_incidents() -> None:
    store = InMemoryIncidentStore()
    sink = CapturingAlertPublisher()
    publisher = IncidentEventPublisher(store, sink)
    event = TelemetryEvent(
        event_id="partial-cli",
        kind=SignalKind.PARTIAL_RESULT,
        request_id="req-partial",
        payload={"status": "success", "resultCount": 0, "cards": []},
    )

    result = run_once([event], AiIncidentDetectorSuite(), publisher)

    assert result.processed == 1
    assert result.published == 1
    assert len(sink.incidents) == 1


def test_polling_loop_uses_telemetry_source_receive_and_ack_contract() -> None:
    store = InMemoryIncidentStore()
    sink = CapturingAlertPublisher()
    publisher = IncidentEventPublisher(store, sink)
    event = TelemetryEvent(
        event_id="partial-source",
        kind=SignalKind.PARTIAL_RESULT,
        request_id="req-source",
        payload={"status": "success", "resultCount": 0, "cards": []},
    )
    source = InMemoryTelemetrySource()
    source.queued.append(event)

    result = run_polling_loop(
        source,
        AiIncidentDetectorSuite(),
        publisher,
        max_messages=1,
        stop_after=1,
    )

    assert result.processed == 1
    assert result.published == 1
    assert source.acked == ["partial-source"]


def test_cli_reliability_eval_outputs_json(capsys) -> None:
    assert main(["run-reliability-eval"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload == {"caseCount": 2, "degradedBehaviorOk": True}
