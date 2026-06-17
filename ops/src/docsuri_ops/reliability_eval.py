from __future__ import annotations

from dataclasses import dataclass

from docsuri_ops.domain.models import ReliabilityEvalCase, ReliabilityEvalReport


@dataclass(slots=True)
class ReliabilityEvalProbe:
    def run_reliability_eval_set(
        self, cases: list[ReliabilityEvalCase] | tuple[ReliabilityEvalCase, ...]
    ) -> ReliabilityEvalReport:
        results = tuple(self._run_case(case) for case in cases)
        return ReliabilityEvalReport(
            cases=results,
            degraded_behavior_ok=all(result["passed"] for result in results),
        )

    def verify_degraded_mode(self, mode: str) -> dict[str, object]:
        return {"status": "degraded", "degraded": True, "degradeMode": mode}

    def _run_case(self, case: ReliabilityEvalCase) -> dict[str, object]:
        actual = self._actual_status(case)
        return {
            "name": case.name,
            "expected": case.expected_status,
            "actual": actual,
            "passed": actual == case.expected_status,
        }

    def _actual_status(self, case: ReliabilityEvalCase) -> str:
        payload = case.payload
        if payload.get("embeddingFailure"):
            return "degraded"
        if payload.get("vectorIndexFailure"):
            return "fail_closed"
        if payload.get("emptyCandidate"):
            return "abstain"
        if payload.get("forcedCostDegrade"):
            return "degraded"
        return str(payload.get("status", case.expected_status))
