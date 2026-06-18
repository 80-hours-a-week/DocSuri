"""US-R4: discovery app metrics must reach the injected ObservabilityHub (not the void).

These pin the wiring seam fixed for US-R4 — the factory ``observability`` arg flows into the
orchestrator's ``emit_metric`` calls. ``RecordingHub`` duck-types ``docsuri_shared.ports``.
"""

from __future__ import annotations

from docsuri_shared.dtos import SearchRequest

from discovery.api import run_search
from discovery.domain.models import AuthSession, RequestContext
from discovery.mocks import build_mock_orchestrator


class RecordingHub:
    """Minimal ObservabilityHub that records emitted metrics (verifies the wiring seam)."""

    def __init__(self) -> None:
        self.metrics: list[tuple[str, float, dict]] = []

    def emit_metric(self, name, value, tags) -> None:
        self.metrics.append((name, value, dict(tags)))

    def emit_log(self, entry) -> None: ...
    def start_span(self, name, context):
        return None

    def audit_append(self, event) -> None: ...


def _ctx() -> RequestContext:
    return RequestContext(auth_session=AuthSession(user_id="u1"), request_id="req-1")


def _run(hub: RecordingHub) -> None:
    bundle = build_mock_orchestrator(observability=hub)
    run_search(
        bundle.orchestrator,
        bundle.grounding_hook,
        SearchRequest(query="diffusion protein structure"),
        _ctx(),
    )


def test_injected_hub_receives_search_candidates_metric() -> None:
    """Wiring seam: the factory's observability arg reaches the orchestrator's emit."""
    hub = RecordingHub()
    _run(hub)
    assert "discovery.search.candidates" in [m[0] for m in hub.metrics]


def test_injected_hub_receives_grounding_health_metric() -> None:
    """US-R4 grounding-health signal (hallucination incident class), emitted on finalize.

    RED until SearchOrchestrationService._emit_grounding_health is implemented. The verdict
    ("pass" here) must be recoverable from the metric name OR a tag value so a CloudWatch
    alarm can route the block/abstain rate to the IR process.
    """
    hub = RecordingHub()
    _run(hub)
    grounding = [m for m in hub.metrics if "grounding" in m[0]]
    assert grounding, "finalize must emit a grounding-health metric carrying the verdict"
    name, _value, tags = grounding[0]
    assert "pass" in name or "pass" in tags.values()


def test_no_match_emits_abstain_grounding_health() -> None:
    """Zero-candidate (no-match) queries are abstains too — they never reach finalize, so the
    no-match branch must still emit grounding-health or the dashboard abstain rate is blind
    to zero-result queries. (US-R4)"""
    hub = RecordingHub()
    bundle = build_mock_orchestrator(observability=hub)
    run_search(
        bundle.orchestrator,
        bundle.grounding_hook,
        SearchRequest(query="zzz nonsense token"),
        _ctx(),
    )
    grounding = [m for m in hub.metrics if "grounding" in m[0]]
    assert any(m[2].get("verdict") == "abstain" for m in grounding), (
        "no-match path must emit a grounding-health metric with verdict=abstain"
    )
