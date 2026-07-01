"""Property-based tests for chunk_id (PBT P2/P3 — deterministic + idempotent key).

TD-8: Hypothesis. The chunk id is the IndexRecord document id / idempotent upsert key,
so it MUST be a pure deterministic function and MUST NOT collide for distinct
(paper_id, ordinal) inputs.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from docsuri_shared.ids import CHUNK_ID_SEPARATOR, chunk_id, paper_id_prefix

# arXiv-id-like alphabet; deliberately EXCLUDES '#' (the separator) — arXiv IDs never
# contain '#', which is exactly why it is an unambiguous separator.
paper_ids = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./_-",
    min_size=1,
    max_size=24,
)
ordinals = st.integers(min_value=0, max_value=10**9)


@given(paper_ids, ordinals)
def test_deterministic_and_format(paper_id, ordinal):
    a = chunk_id(paper_id, ordinal)
    b = chunk_id(paper_id, ordinal)
    assert a == b  # pure / deterministic (PBT P2)
    assert a == f"{paper_id}{CHUNK_ID_SEPARATOR}{ordinal}"


@given(paper_ids, ordinals)
def test_prefix_scans_the_paper(paper_id, ordinal):
    assert chunk_id(paper_id, ordinal).startswith(paper_id_prefix(paper_id))
    assert paper_id_prefix(paper_id) == f"{paper_id}{CHUNK_ID_SEPARATOR}"


@given(paper_ids, ordinals, paper_ids, ordinals)
def test_injective(p1, o1, p2, o2):
    # No collisions: equal ids ⇒ equal inputs (PBT P3 — idempotent upsert correctness).
    if chunk_id(p1, o1) == chunk_id(p2, o2):
        assert (p1, o1) == (p2, o2)


def test_guards():
    with pytest.raises(ValueError):
        chunk_id("", 0)
    with pytest.raises(ValueError):
        chunk_id("2106.01234", -1)
    with pytest.raises(ValueError):
        paper_id_prefix("")
    # A paper_id containing the separator would break injectivity / prefix-scan.
    with pytest.raises(ValueError):
        chunk_id(f"2106{CHUNK_ID_SEPARATOR}01234", 0)
    # bool is an int subclass but is not a valid ordinal; floats render differently.
    with pytest.raises(TypeError):
        chunk_id("2106.01234", True)
    with pytest.raises(TypeError):
        chunk_id("2106.01234", 1.0)
