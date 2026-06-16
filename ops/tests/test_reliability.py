from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from docsuri_ops.detectors import PartialResultDetector
from docsuri_ops.domain.enums import IncidentClass, Severity
from docsuri_ops.domain.models import ReliabilityEvalCase
from docsuri_ops.reliability_eval import ReliabilityEvalProbe


def test_partial_detector_flags_empty_success() -> None:
    detector = PartialResultDetector()

    candidate = detector.evaluate_response(
        request_id="req-empty",
        payload={"status": "success", "resultCount": 0, "cards": []},
        signal_id="partial-1",
    )

    assert candidate is not None
    assert candidate.incident_class == IncidentClass.PARTIAL_RESULT
    assert candidate.severity == Severity.WARNING


def test_partial_detector_flags_retrieval_failure_success() -> None:
    detector = PartialResultDetector()

    candidate = detector.evaluate_response(
        request_id="req-failure",
        payload={"status": "success", "retrievalFailure": True, "cards": [{"id": "x"}]},
        signal_id="partial-2",
    )

    assert candidate is not None
    assert candidate.severity == Severity.CRITICAL


def test_partial_detector_ignores_explicit_abstain_and_degraded_paths() -> None:
    detector = PartialResultDetector()

    assert (
        detector.evaluate_response(
            request_id="req-abstain",
            payload={"status": "abstain", "reason": "no corpus result"},
            signal_id="partial-3",
        )
        is None
    )
    assert (
        detector.evaluate_response(
            request_id="req-degraded",
            payload={"status": "degraded", "degraded": True, "degradeMode": "LEXICAL_ONLY"},
            signal_id="partial-4",
        )
        is None
    )


def test_reliability_eval_probe_runs_qt3_scenarios() -> None:
    probe = ReliabilityEvalProbe()
    report = probe.run_reliability_eval_set(
        [
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
            ReliabilityEvalCase(
                name="empty candidate abstains",
                expected_status="abstain",
                payload={"emptyCandidate": True},
            ),
            ReliabilityEvalCase(
                name="forced cost degrade is explicit",
                expected_status="degraded",
                payload={"forcedCostDegrade": True},
            ),
        ]
    )

    assert report.degraded_behavior_ok
    assert len(report.cases) == 4


@given(st.sampled_from(["abstain", "fail_closed", "failed", "error"]))
def test_partial_detector_does_not_treat_explicit_non_success_as_partial(status: str) -> None:
    detector = PartialResultDetector()

    candidate = detector.evaluate_response(
        request_id="req-property",
        payload={"status": status, "retrievalFailure": True, "resultCount": 0},
        signal_id=f"partial-{status}",
    )

    assert candidate is None
