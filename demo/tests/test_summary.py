"""#02 SummaryService — mock-mode walking-skeleton tests."""

from __future__ import annotations

import pytest

from app.crosscutting.glossary.store import InMemoryGlossary
from app.crosscutting.verifier.port import AlwaysSupportedVerifier
from app.domain.summarization.presets import AnglePreset, LengthPreset
from app.domain.summarization.service import (
    SummaryService,
    SummaryStreamDone,
    SummaryStreamSentence,
)
from app.infra.llm.mock import MockLLM

from .conftest import SAMPLE_PAPER_ID

pytestmark = pytest.mark.asyncio


async def test_summary_returns_anchored_sentences() -> None:
    llm = MockLLM()
    service = SummaryService(
        llm=llm,
        verifier=AlwaysSupportedVerifier(),
        glossary=InMemoryGlossary(),
    )

    result = await service.summarize(
        paper_id=SAMPLE_PAPER_ID,
        length=LengthPreset.PARAGRAPH,
        angle=AnglePreset.CONTRIBUTION,
        session_id="t-summary",
    )

    assert len(result.sentences) >= 1
    first = result.sentences[0]
    assert first.anchor.section_id == "abstract"
    assert "[§abstract]" in first.text  # mock injects the inline anchor too


async def test_summary_second_call_is_cache_hit() -> None:
    llm = MockLLM()
    verifier = AlwaysSupportedVerifier()
    glossary = InMemoryGlossary()
    service = SummaryService(llm=llm, verifier=verifier, glossary=glossary)

    first = await service.summarize(
        paper_id=SAMPLE_PAPER_ID,
        length=LengthPreset.PARAGRAPH,
        angle=AnglePreset.CONTRIBUTION,
        session_id="t-summary-cache",
    )
    second = await service.summarize(
        paper_id=SAMPLE_PAPER_ID,
        length=LengthPreset.PARAGRAPH,
        angle=AnglePreset.CONTRIBUTION,
        session_id="t-summary-cache",
    )

    assert first.cache_hit is False
    assert second.cache_hit is True


async def test_summary_stream_yields_sentence_then_done() -> None:
    """Streaming path: each NDJSON line surfaces as a SummaryStreamSentence."""
    service = SummaryService(
        llm=MockLLM(),
        verifier=AlwaysSupportedVerifier(),
        glossary=InMemoryGlossary(),
    )

    events: list = []
    async for evt in service.summarize_stream(
        paper_id=SAMPLE_PAPER_ID,
        length=LengthPreset.PARAGRAPH,
        angle=AnglePreset.CONTRIBUTION,
        session_id="t-summary-stream",
    ):
        events.append(evt)

    sentence_events = [e for e in events if isinstance(e, SummaryStreamSentence)]
    done_events = [e for e in events if isinstance(e, SummaryStreamDone)]

    assert len(sentence_events) >= 2, "mock LLM emits multiple NDJSON sentence lines"
    assert sentence_events[0].index == 0
    assert sentence_events[1].index == 1
    assert sentence_events[0].sentence.anchor.section_id == "abstract"
    assert sentence_events[0].sentence.verify_label == "SUPPORTED"
    assert len(done_events) == 1, "exactly one terminal done event"
