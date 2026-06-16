"""PBT-03 — RelevanceRanker order stability + top-N truncation (BR-5)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from discovery.domain.models import (
    Candidate,
    CandidateSet,
    DegradationSignal,
    QueryPlan,
    RetrievalMode,
)
from discovery.domain.ranker import TOP_N, RelevanceRanker
from discovery.mocks.fixtures import RECORDS

_ranker = RelevanceRanker()
_plan = QueryPlan(lexical_terms=(), mode=RetrievalMode.HYBRID)
_degradation = DegradationSignal(llm_enabled=True, rerank_enabled=True)
_score_lists = st.lists(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False), max_size=40
)


def _candidates(scores: list[float]) -> CandidateSet:
    cands = tuple(
        Candidate(record=RECORDS[i % len(RECORDS)], retrieval_score=s)
        for i, s in enumerate(scores)
    )
    return CandidateSet(candidates=cands, retrieval_mode=RetrievalMode.HYBRID)


@given(_score_lists)
def test_truncates_to_top_n_and_sorted_descending(scores: list[float]) -> None:
    ranked = _ranker.rank(_candidates(scores), _plan, _degradation, TOP_N)
    assert len(ranked.ranked) <= TOP_N
    out_scores = [c.retrieval_score for c in ranked.ranked]
    assert out_scores == sorted(out_scores, reverse=True)


@given(_score_lists)
def test_order_is_stable_deterministic(scores: list[float]) -> None:
    cset = _candidates(scores)
    first = _ranker.rank(cset, _plan, _degradation, TOP_N).ranked
    second = _ranker.rank(cset, _plan, _degradation, TOP_N).ranked
    assert [c.record.chunkId for c in first] == [c.record.chunkId for c in second]


def test_fewer_than_n_returns_all() -> None:
    ranked = _ranker.rank(_candidates([0.1, 0.2]), _plan, _degradation, TOP_N)
    assert len(ranked.ranked) == 2
