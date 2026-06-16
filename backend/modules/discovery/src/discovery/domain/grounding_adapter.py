"""GroundingAdapter — FR-5 (BR-7/8; INV-1).

THIN adapter only: shapes the U6 enforce input and maps its verdict. It MUST NOT call
``enforce`` (single authority = U6 gateway post-handler) and MUST NOT do its own provenance
check or incident emission. The enforce call is performed by the gateway seam
(``api/router.py`` here, standing in for the U6 gateway) between ``to_grounding_input`` and
``map_decision`` — see service/orchestrator.py (``plan_and_retrieve`` / ``finalize``).
"""

from __future__ import annotations

from docsuri_shared.ports import GroundingDecision

from .models import AbstainResult, GroundedResults, GroundingInput, QueryPlan, RankedResults

# Non-technical abstain reason code (internal violation detail NOT exposed, SEC-9).
ABSTAIN_GROUNDING = "no_grounded_results"


class GroundingAdapter:
    def to_grounding_input(self, ranked: RankedResults, plan: QueryPlan) -> GroundingInput:  # noqa: ARG002
        """Shape enforce input: candidate response + the real records to verify against."""
        retrieved = tuple(c.record for c in ranked.ranked)
        return GroundingInput(candidate_response=ranked, retrieved_records=retrieved)

    def map_decision(
        self, decision: GroundingDecision, ranked: RankedResults
    ) -> GroundedResults | AbstainResult:
        """Map the U6 verdict to a terminal domain result (BR-8). pass→grounded, else→abstain.

        ``ranked`` is the candidate set that was passed to enforce (in scope at the gateway
        seam); ``map_decision`` selects/forwards it rather than re-deriving anything (INV-1).
        """
        if decision.verdict == "pass":
            return GroundedResults(items=ranked.ranked)
        # block | abstain → abstain terminal state (no fabrication; BR-8/10)
        return AbstainResult(reason=ABSTAIN_GROUNDING)
