"""PBT-08 P1: Deduplication state machine idempotency properties.

Verifies that concurrent/retry re-ingestion of the same paper never causes divergent state:
  - Property 1: A fully ingested paper re-evaluated yields DUPLICATE (stable terminal state).
  - Property 2: Re-running the full claim→mark cycle on an already-ingested paper is a no-op.
  - Property 3: A stale (lower) version arriving after a newer version is always rejected.
"""

from __future__ import annotations

import hashlib

from hypothesis import given, settings
from hypothesis import strategies as st

from docsuri_ingestion.adapters.local import InMemoryControlPlaneStore
from docsuri_ingestion.domain.enums import DedupDecision

from .strategies import parsed_paper_strategy


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@given(parsed_paper_strategy())
@settings(max_examples=50, derandomize=True)
def test_p1_ingested_paper_evaluates_as_duplicate(paper) -> None:
    """After claim+mark, the same (id, version, fingerprint) evaluates as DUPLICATE."""
    store = InMemoryControlPlaneStore()
    fp = _fingerprint(paper.full_text)

    store.try_claim_upsert(paper.paper_id, paper.version, fp)
    store.mark_ingested(paper.paper_id, paper.version, fp)

    result = store.evaluate_dedup(paper.paper_id, paper.version, fp)
    assert result.decision is DedupDecision.DUPLICATE


@given(parsed_paper_strategy())
@settings(max_examples=50, derandomize=True)
def test_p1_repeated_claim_mark_cycle_is_idempotent(paper) -> None:
    """Running try_claim → mark_ingested N times converges to the same state."""
    store = InMemoryControlPlaneStore()
    fp = _fingerprint(paper.full_text)

    store.try_claim_upsert(paper.paper_id, paper.version, fp)
    store.mark_ingested(paper.paper_id, paper.version, fp)
    state_after_first = store.dedup_states[paper.paper_id]

    for _ in range(3):
        store.try_claim_upsert(paper.paper_id, paper.version, fp)
        store.mark_ingested(paper.paper_id, paper.version, fp)

    state_after_repeats = store.dedup_states[paper.paper_id]
    assert state_after_repeats.current_version == state_after_first.current_version
    assert state_after_repeats.fingerprint == state_after_first.fingerprint
    assert state_after_repeats.state == state_after_first.state


@given(
    parsed_paper_strategy(),
    st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50, derandomize=True)
def test_p1_stale_version_never_overwrites_newer(paper, extra_versions) -> None:
    """A paper with version N already ingested rejects version < N (STALE)."""
    store = InMemoryControlPlaneStore()
    newer_version = paper.version + extra_versions
    fp_newer = _fingerprint(f"{paper.full_text}-v{newer_version}")

    store.try_claim_upsert(paper.paper_id, newer_version, fp_newer)
    store.mark_ingested(paper.paper_id, newer_version, fp_newer)

    fp_stale = _fingerprint(paper.full_text)
    result = store.evaluate_dedup(paper.paper_id, paper.version, fp_stale)
    assert result.decision is DedupDecision.STALE

    claim_result = store.try_claim_upsert(paper.paper_id, paper.version, fp_stale)
    assert claim_result is False

    final_state = store.dedup_states[paper.paper_id]
    assert final_state.current_version == newer_version
