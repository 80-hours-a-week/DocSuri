"""TranslationService — span → 한국어 + glossary additions.

Walking-skeleton for #03 Sprint 1. Composition:

  SpanResolver → glossary.list → prompts.build → llm.complete
                                              → 종결형 post-processor
                                              → glossary.add for new terms

§4.1: cache key derivation lives in `infra/llm`. This service never sees one.
§6.2: any English word matched as a domain term but missing from the
       session glossary is added so subsequent calls reuse the mapping.
§6.3: `-합니다` 체 → `-한다` 체 post-processor enforced regardless of
       LLM output style.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from app.crosscutting.glossary.protocol import GlossaryPort
from app.domain.papers.models import GlossaryEntry
from app.domain.translation import prompts
from app.domain.translation.span import SpanResolver
from app.infra.llm.protocol import LLMPort


class TranslationResult(BaseModel):
    english: str
    korean: str
    glossary_additions: list[GlossaryEntry] = []
    cache_hit: bool
    model: str


# Best-effort heuristic terms the post-processor can detect in the
# *English* span so that newly-seen domain words get persisted to the
# session glossary even when the LLM forgets to declare them. Sprint 2
# will replace this with a proper structured response.
_CANDIDATE_TERMS = [
    "transformer",
    "attention",
    "embedding",
    "self-attention",
    "encoder",
    "decoder",
    "token",
    "neural network",
    "language model",
    "fine-tuning",
    "pre-training",
    "loss function",
    "gradient descent",
    "softmax",
]

# Fallback dictionary mirrors the mock LLM — used only when proposing a
# glossary addition for a term the LLM neglected to declare.
_FALLBACK_KO = {
    "transformer": "트랜스포머",
    "attention": "주의",
    "embedding": "임베딩",
    "self-attention": "자기 주의",
    "encoder": "인코더",
    "decoder": "디코더",
    "token": "토큰",
    "neural network": "신경망",
    "language model": "언어 모델",
    "fine-tuning": "미세 조정",
    "pre-training": "사전 학습",
    "loss function": "손실 함수",
    "gradient descent": "경사 하강법",
    "softmax": "소프트맥스",
}


def _enforce_hada_che(text: str) -> str:
    """Post-process 합니다체 → 한다체 (AGENTS.md §6.3)."""

    text = re.sub(r"합니다([.?!]?)", r"한다\1", text)
    text = re.sub(r"입니다([.?!]?)", r"이다\1", text)
    text = re.sub(r"됩니다([.?!]?)", r"된다\1", text)
    text = re.sub(r"있습니다([.?!]?)", r"있다\1", text)
    text = re.sub(r"없습니다([.?!]?)", r"없다\1", text)
    return text


class TranslationService:
    def __init__(self, llm: LLMPort, glossary: GlossaryPort) -> None:
        self._llm = llm
        self._glossary = glossary
        self._resolver = SpanResolver()

    async def translate(
        self,
        paper_id: str,
        section_id: str,
        char_start: int,
        char_end: int,
        session_id: str = "default",
    ) -> TranslationResult:
        span = await self._resolver.resolve(
            paper_id, section_id, char_start, char_end
        )
        glossary_entries = await self._glossary.list_for_session(session_id)

        req = prompts.build_translate_prompt(
            span=span,
            glossary_entries=glossary_entries,
        )
        resp = await self._llm.complete(req)
        korean = _enforce_hada_che(resp.text)

        additions = await self._record_new_terms(
            session_id=session_id,
            english_span=span.span_text,
            paper_id=paper_id,
        )

        return TranslationResult(
            english=span.span_text,
            korean=korean,
            glossary_additions=additions,
            cache_hit=resp.cache_hit,
            model=resp.model,
        )

    async def _record_new_terms(
        self,
        session_id: str,
        english_span: str,
        paper_id: str,
    ) -> list[GlossaryEntry]:
        """For each candidate domain term in the span not yet in glossary,
        register the fallback Korean mapping.

        First-occurrence detection per §6.2 — once recorded the
        glossary's `add` is a no-op (first-write-wins in `store.py`).
        """

        additions: list[GlossaryEntry] = []
        lowered = english_span.lower()
        for term in sorted(_CANDIDATE_TERMS, key=lambda t: -len(t)):
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                existing = await self._glossary.lookup(session_id, term)
                if existing is None:
                    entry = GlossaryEntry(
                        english=term,
                        korean=_FALLBACK_KO.get(term, term),
                        first_seen_paper_id=paper_id,
                    )
                    await self._glossary.add(session_id, entry)
                    additions.append(entry)
        return additions
