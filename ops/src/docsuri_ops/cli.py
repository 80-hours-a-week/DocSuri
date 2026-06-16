from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

from docsuri_ops.adapters.local import CapturingAlertPublisher, InMemoryIncidentStore
from docsuri_ops.cost_guard import CostGuardCircuitBreaker
from docsuri_ops.dashboard import OpsDashboardService
from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import (
    DashboardWindow,
    ReliabilityEvalCase,
    TelemetryEvent,
    UsageEvent,
)
from docsuri_ops.grounding import GroundingEnforcementHook
from docsuri_ops.incidents import AiIncidentDetectorSuite, IncidentEventPublisher
from docsuri_ops.reliability_eval import ReliabilityEvalProbe
from docsuri_ops.worker import run_once


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsuri-ops")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-detectors")
    subparsers.add_parser("run-grounding-eval")
    subparsers.add_parser("run-reliability-eval")
    subparsers.add_parser("dashboard-summary")

    args = parser.parse_args(argv)
    if args.command == "run-detectors":
        print(json.dumps(_run_detectors(), sort_keys=True))
    elif args.command == "run-grounding-eval":
        print(json.dumps(_run_grounding_eval(), sort_keys=True))
    elif args.command == "run-reliability-eval":
        print(json.dumps(_run_reliability_eval(), sort_keys=True))
    elif args.command == "dashboard-summary":
        print(json.dumps(_dashboard_summary(), sort_keys=True))
    return 0


def _run_detectors() -> dict[str, int]:
    guard = CostGuardCircuitBreaker()
    state = guard.record_spend(UsageEvent(event_id="cli-seed", amount_usd=1300, source="cli"))
    store = InMemoryIncidentStore()
    publisher = IncidentEventPublisher(store, CapturingAlertPublisher())
    event = TelemetryEvent(
        event_id="cli-usage",
        kind=SignalKind.USAGE,
        request_id="cli-request",
        value=10.0,
        payload={"source": "cli"},
    )
    result = run_once([event], AiIncidentDetectorSuite(), publisher, budget_state=state)
    return {"processed": result.processed, "published": result.published}


def _run_grounding_eval() -> dict:
    return GroundingEnforcementHook().run_eval_set(
        [
            {
                "name": "out-of-corpus",
                "candidate": {"answer": "No result"},
                "retrieved": [],
                "expected": "abstain",
            }
        ]
    )


def _run_reliability_eval() -> dict:
    report = ReliabilityEvalProbe().run_reliability_eval_set(
        (
            ReliabilityEvalCase(
                name="embedding failure falls back",
                expected_status="degraded",
                payload={"embeddingFailure": True},
            ),
            ReliabilityEvalCase(
                name="vector index failure fails closed",
                expected_status="fail_closed",
                payload={"vectorIndexFailure": True},
            ),
        )
    )
    return {
        "caseCount": len(report.cases),
        "degradedBehaviorOk": report.degraded_behavior_ok,
    }


def _dashboard_summary() -> dict[str, int]:
    now = datetime.now(UTC)
    dashboard = OpsDashboardService(InMemoryIncidentStore())
    view = dashboard.get_dashboard(DashboardWindow(now - timedelta(hours=1), now))
    return {"incidentCount": view.incident_count, "alertCount": view.alert_count}


if __name__ == "__main__":
    raise SystemExit(main())
