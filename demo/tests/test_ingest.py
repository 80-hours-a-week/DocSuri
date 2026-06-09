"""Tests for the Sprint 1 ingest orchestrator (BE-Ingest scope).

Three goals (DoD-aligned):

1. Abstract-only fallback produces a well-formed :class:`Paper` with at
   least one section when ``GROBID_URL`` is unset.
2. Chunk anchors are unique-per-chunk within a paper.
3. SSE event payload shape matches the contract the FE consumes.
"""

from __future__ import annotations

import json
import os

import pytest

from app.crosscutting.events.bus import EventBus
from app.domain.papers.ingest import (
    PROGRESS_TOPIC,
    STAGE_DONE,
    STAGE_FAILED,
    STAGE_STARTED,
    IngestService,
)
from app.domain.papers.models import PaperSummary
from app.infra.storage.memory import PaperStore


@pytest.fixture(autouse=True)
def _no_grobid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the abstract-only fallback path for every test."""
    monkeypatch.delenv("GROBID_URL", raising=False)
    assert os.getenv("GROBID_URL") is None


def _summary(**overrides) -> PaperSummary:
    defaults = dict(
        id="arxiv:2406.00001",
        source="arxiv",
        title="A Test Paper",
        authors=["Ada Lovelace"],
        abstract=(
            "First sentence introduces the topic. "
            "Second sentence motivates the method. "
            "Third sentence summarises results."
        ),
        year=2026,
        pdf_url=None,
    )
    defaults.update(overrides)
    return PaperSummary(**defaults)


@pytest.mark.asyncio
async def test_abstract_only_fallback_produces_paper() -> None:
    """GROBID_URL unset → fallback synthesises ≥1 section from the abstract."""
    svc = IngestService(event_bus=EventBus(), paper_store=PaperStore())

    paper = await svc.ingest(_summary())

    assert paper.summary.id == "arxiv:2406.00001"
    assert paper.ingested_at is not None
    assert len(paper.sections) >= 1
    abstract = paper.sections[0]
    assert abstract.section_id == "abstract"
    # The 3-sentence abstract should split into ≥1 paragraph (sentences).
    assert len(abstract.paragraphs) >= 1
    assert len(paper.chunks) >= 1


@pytest.mark.asyncio
async def test_chunk_ids_are_unique_within_paper() -> None:
    """Every chunk has a stable, unique ``chunk_id`` (Sprint 2 idempotency primer)."""
    long_abstract = (
        "Sentence one. " + ("Filler word " * 80)
    ).strip()
    svc = IngestService(event_bus=EventBus(), paper_store=PaperStore())

    paper = await svc.ingest(_summary(abstract=long_abstract))

    ids = [c.chunk_id for c in paper.chunks]
    assert len(ids) == len(set(ids)), f"duplicate chunk_ids: {ids}"
    # All chunks belong to the paper.
    assert all(c.paper_id == paper.summary.id for c in paper.chunks)
    # Every chunk carries an anchor with a section_id matching one of the paper's sections.
    section_ids = {s.section_id for s in paper.sections}
    assert all(c.anchor.section_id in section_ids for c in paper.chunks)


@pytest.mark.asyncio
async def test_sse_payload_shape_matches_contract() -> None:
    """Bus payload contains the keys the SSE endpoint forwards verbatim.

    The contract documented in the BE-Ingest spec is::

        data: {"paper_id":"x","stage":"parsing","message":"..."}

    Done stage additionally carries ``section_count`` and ``chunk_count``.
    We collect every published event by subscribing before ingest starts.
    """
    event_bus = EventBus()
    collected: list[dict] = []

    async def _collect(evt) -> None:
        collected.append(evt.payload)

    event_bus.subscribe(PROGRESS_TOPIC, _collect)

    svc = IngestService(event_bus=event_bus, paper_store=PaperStore())
    await svc.ingest(_summary())

    # Sanity: at least started + done.
    assert collected, "no events were published"
    stages = [p["stage"] for p in collected]
    assert stages[0] == STAGE_STARTED
    assert STAGE_DONE in stages
    assert STAGE_FAILED not in stages

    # Every payload satisfies the base shape.
    for payload in collected:
        assert set(["paper_id", "stage", "message"]).issubset(payload.keys())
        assert payload["paper_id"] == "arxiv:2406.00001"
        assert isinstance(payload["message"], str)
        # Payload must JSON-serialise cleanly (SSE sends it as a JSON string).
        round_tripped = json.loads(json.dumps(payload))
        assert round_tripped == payload

    done_payload = next(p for p in collected if p["stage"] == STAGE_DONE)
    assert done_payload["section_count"] >= 1
    assert done_payload["chunk_count"] >= 1
