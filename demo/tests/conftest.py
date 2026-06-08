"""Shared fixtures: seed a single paper into the in-memory store."""

from __future__ import annotations

import pytest

from app.domain.papers.models import Paper, PaperSummary, Section
from app.infra.storage.memory import store

SAMPLE_PAPER_ID = "demo-1706.03762"


@pytest.fixture(autouse=True)
async def _seed_paper() -> None:
    """Per-test seed of the canonical demo paper."""

    paper = Paper(
        summary=PaperSummary(
            id=SAMPLE_PAPER_ID,
            source="arxiv",
            title="Attention Is All You Need",
            authors=["Vaswani et al."],
            abstract=(
                "The dominant sequence transduction models are based on complex "
                "recurrent or convolutional neural networks. We propose a new "
                "simple network architecture, the Transformer, based solely on "
                "attention mechanisms, dispensing with recurrence and "
                "convolutions entirely."
            ),
        ),
        sections=[
            Section(
                section_id="1",
                title="Introduction",
                paragraphs=[
                    "Recurrent neural networks have firmly established themselves "
                    "as state of the art approaches in sequence modeling."
                ],
            ),
            Section(
                section_id="3.2",
                title="Attention",
                paragraphs=[
                    "An attention function can be described as mapping a query "
                    "and a set of key-value pairs to an output."
                ],
            ),
        ],
    )
    await store.put(paper)
    yield
    # Drop the paper to avoid bleed-through between tests.
    store._papers.pop(SAMPLE_PAPER_ID, None)  # noqa: SLF001
