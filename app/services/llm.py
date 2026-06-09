from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from anthropic import AsyncAnthropic

from app.config import Settings
from app.models import AnglePreset, GlossaryTerm, LengthPreset, PaperChunk, PaperDocument
from app.services.anchors import split_sentences


class LLMClient(ABC):
    @abstractmethod
    async def summarize(
        self,
        paper: PaperDocument,
        length_preset: LengthPreset,
        angle_preset: AnglePreset,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def translate(
        self,
        paper: PaperDocument,
        source_text: str,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> str:
        raise NotImplementedError


class AnthropicLLMClient(LLMClient):
    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AnthropicLLMClient")
        self.settings = settings
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def summarize(
        self,
        paper: PaperDocument,
        length_preset: LengthPreset,
        angle_preset: AnglePreset,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> list[str]:
        length_rules = {
            LengthPreset.tldr: "1 sentence, TL;DR style.",
            LengthPreset.paragraph: "3-5 Korean sentences, roughly 150-200 Korean characters.",
            LengthPreset.page: "8-12 Korean sentences, roughly 800-1200 Korean characters.",
        }
        angle_rules = {
            AnglePreset.contribution: "Focus on the paper's core contribution and novelty.",
            AnglePreset.method: "Focus on the method, pipeline, assumptions, and implementation detail.",
            AnglePreset.results: "Focus on results, experiments, comparisons, and evidence.",
            AnglePreset.critical: "Focus on limitations, assumptions, reproducibility risks, and critical review.",
        }
        glossary_text = "\n".join(f"- {term.source}: {term.target}" for term in glossary) or "(empty)"
        context_text = _format_context_chunks(context_chunks)
        response = await self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            system=[
                {
                    "type": "text",
                    "text": (
                        "You summarize academic papers in Korean. Every output sentence must include at least "
                        "one citation anchor copied from the paper, such as [§1.1] or [p.3 ¶2]. "
                        "Prioritize the retrieved context chunks as evidence. Do not cite anchors that are not "
                        "present in the retrieved context or paper text. "
                        "Return strict JSON: {\"sentences\": [\"...\"]}. Do not include prose outside JSON."
                    ),
                },
                {
                    "type": "text",
                    "text": f"Paper title: {paper.title}\n\nPaper text:\n{paper.text[:120000]}",
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"Retrieved context chunks:\n{context_text}",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Length: {length_rules[length_preset]}\n"
                        f"Angle: {angle_rules[angle_preset]}\n"
                        f"Session glossary:\n{glossary_text}\n"
                    ),
                }
            ],
        )
        return _parse_json_sentences(_message_text(response))

    async def translate(
        self,
        paper: PaperDocument,
        source_text: str,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> str:
        glossary_text = "\n".join(f"- {term.source}: {term.target}" for term in glossary) or "(empty)"
        context_text = _format_context_chunks(context_chunks)
        response = await self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            system=[
                {
                    "type": "text",
                    "text": (
                        "Translate selected academic-paper spans into Korean. Use formal '-한다' academic style. "
                        "Preserve LaTeX, citation markers, numbers, and proper nouns. Use retrieved context chunks "
                        "only to disambiguate terminology and surrounding concepts; translate the source span, not "
                        "the context itself. Return strict JSON: "
                        "{\"translation\": \"...\"}. Do not include prose outside JSON."
                    ),
                },
                {
                    "type": "text",
                    "text": f"Paper title: {paper.title}\n\nPaper text:\n{paper.text[:120000]}",
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"Retrieved context chunks:\n{context_text}",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Session glossary:\n{glossary_text}\n\nSource span:\n{source_text}",
                }
            ],
        )
        return _parse_json_translation(_message_text(response))


class MockLLMClient(LLMClient):
    async def summarize(
        self,
        paper: PaperDocument,
        length_preset: LengthPreset,
        angle_preset: AnglePreset,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> list[str]:
        count = {LengthPreset.tldr: 1, LengthPreset.paragraph: 3, LengthPreset.page: 8}[length_preset]
        chunks = context_chunks or paper.chunks or []
        if angle_preset == AnglePreset.critical:
            chunks = chunks[-2:] + chunks[:2]
        elif angle_preset == AnglePreset.method:
            chunks = [chunk for chunk in chunks if re.search("method|pipeline|prompt|model", chunk.text, re.I)] or chunks
        elif angle_preset == AnglePreset.results:
            chunks = [chunk for chunk in chunks if re.search("experiment|result|show|evaluation", chunk.text, re.I)] or chunks

        if not chunks:
            chunks = _chunks_from_plain_text(paper)
        sentences = []
        for chunk in chunks[:count]:
            korean = _demo_korean_sentence(chunk.text)
            sentences.append(f"{korean} [{chunk.anchor}]")
        return sentences

    async def translate(
        self,
        paper: PaperDocument,
        source_text: str,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> str:
        text = source_text
        for term in sorted(glossary, key=lambda item: len(item.source), reverse=True):
            replacement = f"{term.target}({term.source})" if term.first_seen else term.target
            text = re.sub(rf"\b{re.escape(term.source)}\b", replacement, text, flags=re.IGNORECASE)
        return f"데모 번역: {text}".strip()


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.use_anthropic:
        return AnthropicLLMClient(settings)
    return MockLLMClient()


def _message_text(response: object) -> str:
    chunks = getattr(response, "content", [])
    return "".join(getattr(chunk, "text", "") for chunk in chunks)


def _format_context_chunks(chunks: list[PaperChunk]) -> str:
    if not chunks:
        return "(empty)"
    parts = []
    for chunk in chunks:
        label = chunk.anchor
        if chunk.section:
            label = f"{label} section={chunk.section}"
        if chunk.page is not None:
            label = f"{label} page={chunk.page}"
        parts.append(f"[{label}]\n{chunk.text}")
    return "\n\n".join(parts)


def _parse_json_sentences(text: str) -> list[str]:
    payload = _loads_json(text)
    sentences = payload.get("sentences", [])
    if not isinstance(sentences, list) or not all(isinstance(sentence, str) for sentence in sentences):
        raise ValueError("LLM summary response must contain a string array at 'sentences'.")
    return sentences


def _parse_json_translation(text: str) -> str:
    payload = _loads_json(text)
    translation = payload.get("translation")
    if not isinstance(translation, str):
        raise ValueError("LLM translation response must contain a string at 'translation'.")
    return translation


def _loads_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _chunks_from_plain_text(paper: PaperDocument):
    from app.models import PaperChunk

    chunks = []
    for idx, sentence in enumerate(split_sentences(paper.text), start=1):
        chunks.append(PaperChunk(paper_id=paper.id, text=sentence, anchor=f"§{idx}.1"))
    return chunks


def _demo_korean_sentence(text: str) -> str:
    lowered = text.lower()
    if "limitation" in lowered or "dependence" in lowered:
        return "이 논문은 추출 품질과 검증 비용 같은 한계를 명시한다"
    if "experiment" in lowered or "show" in lowered:
        return "실험은 anchor 검증이 근거 없는 주장을 줄이고 신뢰를 높인다는 점을 보인다"
    if "method" in lowered or "fetch" in lowered:
        return "방법은 구조화된 본문과 관련 청크를 가져와 cached prompt로 anchor가 포함된 요약을 생성한다"
    return "이 논문은 PostgreSQL 원본 PDF와 PGVector 청크를 활용하는 논문 요약 및 번역 워크플로를 제안한다"
