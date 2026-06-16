"""RelevanceRanker — FR-3 / Q3=A, Q10=A (BR-5; PBT-03).

Baseline ranking only: sort by merge (RRF) score descending, truncate to top-N=20. NO LLM
rerank (Q3=A) — so the cost-degrade RERANK_OFF tier is a no-op for U2 (handled as a banner
in the assembler). Deterministic stable order with a PaperId tie-break (PBT-03). If fewer
than N candidates, return all (no padding, US-D3).
"""

from __future__ import annotations

from .models import CandidateSet, QueryPlan, RankedResults

TOP_N = 20  # FR-3 (Q10=A)


class RelevanceRanker:
    def rank(
        self,
        candidate_set: CandidateSet,
        plan: QueryPlan,  # noqa: ARG002 — reserved (filter hints); baseline ignores
        degradation,  # noqa: ARG002 — RERANK_OFF is a no-op for the baseline ranker
        top_n: int = TOP_N,
    ) -> RankedResults:
        ranked = sorted(
            candidate_set.candidates,
            key=lambda c: (-c.retrieval_score, c.record.paperId),
        )[:top_n]
        return RankedResults(ranked=tuple(ranked), ranking_mode="baseline")
