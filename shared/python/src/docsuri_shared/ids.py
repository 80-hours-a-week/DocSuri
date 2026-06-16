"""Deterministic identifier helpers for the shared index (vector-spec.md §2).

``chunk_id`` is the IndexRecord document ID and the idempotent upsert key: the same
``(paper_id, ordinal)`` always maps to the same id, so re-ingesting a paper upserts
in place rather than duplicating (BR-5, BR-9; PBT P2/P3). It is SEC-9-internal — it
is never exposed in any DTO — so encoding ``paper_id`` in it is safe.

Scheme (team decision): ``f"{paper_id}#{ordinal}"``. ``#`` never appears in an arXiv
ID, so it is an unambiguous separator and ``f"{paper_id}#"`` is a prefix that scans
exactly the chunks of one paper (supports BR-14 per-paperId tombstone/delete).
The scheme is effectively frozen: changing it changes every document ID ⇒ full reindex.
"""

from __future__ import annotations

__all__ = ["CHUNK_ID_SEPARATOR", "chunk_id", "paper_id_prefix"]

CHUNK_ID_SEPARATOR = "#"


def chunk_id(paper_id: str, ordinal: int) -> str:
    """Return the deterministic chunk/document id for ``(paper_id, ordinal)``.

    Raises ``ValueError`` for an empty ``paper_id`` or a negative ``ordinal`` (fail
    closed — these can never be valid index keys), and ``TypeError`` if ``ordinal`` is
    not an ``int`` (guards against ``bool`` and accidental float ordinals that would
    render differently).
    """
    if not paper_id:
        raise ValueError("paper_id must be non-empty")
    if CHUNK_ID_SEPARATOR in paper_id:
        # arXiv IDs never contain '#'; enforce it so the separator stays unambiguous
        # and the id stays injective / prefix-scannable (the contract this relies on).
        raise ValueError(
            f"paper_id must not contain the {CHUNK_ID_SEPARATOR!r} separator: {paper_id!r}"
        )
    if isinstance(ordinal, bool) or not isinstance(ordinal, int):
        raise TypeError(f"ordinal must be an int, got {type(ordinal).__name__}")
    if ordinal < 0:
        raise ValueError(f"ordinal must be non-negative, got {ordinal}")
    return f"{paper_id}{CHUNK_ID_SEPARATOR}{ordinal}"


def paper_id_prefix(paper_id: str) -> str:
    """Return the ``chunk_id`` prefix matching all chunks of ``paper_id``.

    Every ``chunk_id(paper_id, n)`` starts with this prefix — use it for the BR-14
    per-paperId delete/tombstone scan.
    """
    if not paper_id:
        raise ValueError("paper_id must be non-empty")
    return f"{paper_id}{CHUNK_ID_SEPARATOR}"
