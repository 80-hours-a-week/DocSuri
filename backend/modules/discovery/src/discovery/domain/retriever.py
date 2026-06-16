"""HybridRetriever — FR-2 / Q2=A (BR-4; PBT-07).

k-NN ∥ BM25 → Reciprocal Rank Fusion (scale-invariant) → PaperId-level dedup (one record
per paper; many chunks per paper in the index). Idempotent + resultset-preserving (PBT-07):
the output PaperId set equals the union of input PaperId sets, each exactly once.

In lexical-only mode (cost degrade or embedding fallback) only BM25 runs. Any store error
raises ``IndexUnavailable`` (OpenSearch = one store for both k-NN and BM25) → fail-closed.
"""

from __future__ import annotations

from .models import Candidate, CandidateSet, QueryPlan, RetrievalMode

# k-NN/BM25 candidate breadth before fusion (> top-N so ranking has headroom). NFR/Infra tune.
RETRIEVAL_TOP_K = 50
# RRF constant (standard default). NFR/Infra tune.
RRF_K = 60


class HybridRetriever:
    def __init__(self, vector_store, lexical_index) -> None:
        # Typed as ports.VectorStoreAdapter / LexicalIndexAdapter; duck-typed for mock/real.
        self._vector_store = vector_store
        self._lexical_index = lexical_index

    def retrieve(self, plan: QueryPlan, degradation) -> CandidateSet:  # noqa: ARG002
        result_lists = []
        if plan.mode is RetrievalMode.HYBRID and plan.embedding_vector is not None:
            result_lists.append(
                self._vector_store.knn_search(plan.embedding_vector, RETRIEVAL_TOP_K)
            )
        result_lists.append(self._lexical_index.bm25_search(plan.lexical_terms, RETRIEVAL_TOP_K))

        fused = _reciprocal_rank_fusion(result_lists)
        mode = RetrievalMode.HYBRID if len(result_lists) > 1 else RetrievalMode.LEXICAL_ONLY
        return CandidateSet(candidates=fused, retrieval_mode=mode)


def _reciprocal_rank_fusion(result_lists) -> tuple[Candidate, ...]:
    """Merge ranked lists by RRF and dedup by PaperId (BR-4; PBT-07).

    score(paper) = Σ_list 1 / (RRF_K + rank_in_list). One record kept per PaperId (first
    seen — deterministic). Sorted by (-score, paperId) so ties are deterministic.
    """
    scores: dict[str, float] = {}
    best_record: dict[str, object] = {}
    for results in result_lists:
        for rank, (record, _store_score) in enumerate(results):
            pid = record.paperId
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)
            if pid not in best_record:
                best_record[pid] = record
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return tuple(
        Candidate(record=best_record[pid], retrieval_score=score) for pid, score in ordered
    )
