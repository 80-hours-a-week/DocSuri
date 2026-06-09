from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod

from app.config import Settings
from app.models import AnglePreset, GlossaryTerm, LengthPreset, PaperChunk, PaperDocument
from app.services.bedrock import build_bedrock_runtime_client


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


class BedrockClaudeLLMClient(LLMClient):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = build_bedrock_runtime_client(settings)

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
        text = await self._converse(
            model_id=self.settings.anthropic_model,
            system=[
                (
                    "You summarize academic papers in Korean. Every output sentence must include at least "
                    "one citation anchor copied from the paper, such as [§1.1] or [p.3 ¶2]. "
                    "Prioritize the retrieved context chunks as evidence. Do not cite anchors that are not "
                    "present in the retrieved context or paper text. "
                    'Return strict JSON: {"sentences": ["..."]}. Do not include prose outside JSON.'
                ),
                f"Paper title: {paper.title}\n\nPaper text:\n{paper.text[:120000]}",
                f"Retrieved context chunks:\n{_format_context_chunks(context_chunks)}",
            ],
            user_text=(
                f"Length: {length_rules[length_preset]}\n"
                f"Angle: {angle_rules[angle_preset]}\n"
                f"Session glossary:\n{glossary_text}\n"
            ),
        )
        return _parse_json_sentences(text)

    async def translate(
        self,
        paper: PaperDocument,
        source_text: str,
        glossary: list[GlossaryTerm],
        context_chunks: list[PaperChunk],
    ) -> str:
        glossary_text = "\n".join(f"- {term.source}: {term.target}" for term in glossary) or "(empty)"
        text = await self._converse(
            model_id=self.settings.anthropic_model,
            system=[
                (
                    "Translate selected academic-paper spans into Korean. Use formal '-한다' academic style. "
                    "Preserve LaTeX, citation markers, numbers, and proper nouns. Use retrieved context chunks "
                    "only to disambiguate terminology and surrounding concepts; translate the source span, not "
                    'the context itself. Return strict JSON: {"translation": "..."}. Do not include prose outside JSON.'
                ),
                f"Paper title: {paper.title}\n\nPaper text:\n{paper.text[:120000]}",
                f"Retrieved context chunks:\n{_format_context_chunks(context_chunks)}",
            ],
            user_text=f"Session glossary:\n{glossary_text}\n\nSource span:\n{source_text}",
        )
        return _parse_json_translation(text)

    async def _converse(self, model_id: str, system: list[str], user_text: str) -> str:
        response = await asyncio.to_thread(
            self.client.converse,
            modelId=model_id,
            system=[{"text": item} for item in system],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig={
                "maxTokens": self.settings.llm_max_tokens,
                "temperature": self.settings.llm_temperature,
            },
        )
        return _converse_text(response)


def build_llm_client(settings: Settings) -> LLMClient:
    return BedrockClaudeLLMClient(settings)


def _converse_text(response: dict) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    return "".join(part.get("text", "") for part in content)


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
