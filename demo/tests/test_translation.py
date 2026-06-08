"""#03 TranslationService — mock-mode walking-skeleton tests."""

from __future__ import annotations

import pytest

from app.crosscutting.glossary.store import InMemoryGlossary
from app.domain.translation.service import TranslationService
from app.infra.llm.mock import MockLLM
from app.infra.storage.memory import store

from .conftest import SAMPLE_PAPER_ID

pytestmark = pytest.mark.asyncio


async def test_translate_attention_via_seeded_glossary() -> None:
    llm = MockLLM()
    glossary = InMemoryGlossary()
    service = TranslationService(llm=llm, glossary=glossary)

    paper = await store.get(SAMPLE_PAPER_ID)
    assert paper is not None
    abstract = paper.summary.abstract
    # Locate the word "attention" in the abstract.
    start = abstract.lower().index("attention")
    end = start + len("attention")

    result = await service.translate(
        paper_id=SAMPLE_PAPER_ID,
        section_id="abstract",
        char_start=start,
        char_end=end,
        session_id="t-translate",
    )

    # Sliced English span is exactly the word we requested.
    assert result.english.lower() == "attention"
    # MockLLM substitutes via the pre-seeded glossary.
    assert "주의" in result.korean


async def test_translate_enforces_hada_che() -> None:
    """Manually exercise the -합니다 → -한다 post-processor."""

    from app.domain.translation.service import _enforce_hada_che

    raw = "본 연구에서는 새로운 모델을 제안합니다."
    fixed = _enforce_hada_che(raw)
    assert fixed.endswith("제안한다.")


async def test_translate_invalid_span_raises() -> None:
    llm = MockLLM()
    service = TranslationService(llm=llm, glossary=InMemoryGlossary())

    with pytest.raises(ValueError):
        await service.translate(
            paper_id=SAMPLE_PAPER_ID,
            section_id="abstract",
            char_start=10_000,
            char_end=10_001,
            session_id="t-translate-bad",
        )
