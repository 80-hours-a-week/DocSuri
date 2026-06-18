"""Integration tests against REAL dependencies (real-first, Q14/Q7-Q10 infra).

These exercise the shipped adapters (Bedrock/S3/Redis/RDS). They SELF-SKIP when the
required clients (boto3/redis/psycopg) or credentials/endpoints are absent — so a bare
checkout / unit CI lane stays green; the integration gate lane runs them with scoped creds.
"""

from __future__ import annotations

import os

import pytest


def _missing(mod: str) -> bool:
    try:
        __import__(mod)
        return False
    except ImportError:
        return True


pytestmark = pytest.mark.skipif(
    _missing("boto3") or not os.environ.get("DOCSURI_SUMMARY_BUCKET"),
    reason="real integration deps/creds absent (boto3 / DOCSURI_SUMMARY_BUCKET) — gate lane only",
)


def test_real_bundle_builds() -> None:
    from docsuri_shared.ports import CostGuardCircuitBreaker  # noqa: F401

    from summarization.adapters.settings import SummarizationSettings
    from summarization.real_wiring import build_real_orchestrator

    settings = SummarizationSettings.from_env()
    assert settings.summarization_enabled

    class _Budget:
        degrade_mode = "normal"
        circuit_state = "closed"
        tier = "normal"

    class _Cost:
        def get_budget_state(self):
            return _Budget()

    class _Obs:
        def emit_metric(self, *a, **k):
            pass

        def emit_log(self, *a, **k):
            pass

        def start_span(self, *a, **k):
            return None

        def audit_append(self, *a, **k):
            pass

    bundle = build_real_orchestrator(settings, cost_guard=_Cost(), observability=_Obs())
    assert bundle.orchestrator is not None
