"""Persona-aware paper summary engine for U2."""

from __future__ import annotations

import json
import re
import time

from docsuri.u0.ports import CachePort, Glossary, LlmPort, Persona, Telemetry, TelemetryEvent

from .glossary_tools import glossary_hits
from .models import PaperText, SummaryResult, SummarySections, UsageCost
from .prompts import build_summary_prompt
from .readability import ReadabilityValidator

SUMMARY_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_SUMMARY_BUDGET_TOKENS = 1200
MAX_COMPRESSED_CHARS = 10_000


class SummaryEngine:
    def __init__(
        self,
        llm: LlmPort,
        cache: CachePort,
        glossary: Glossary,
        telemetry: Telemetry,
        validator: ReadabilityValidator | None = None,
        budget_tokens: int = DEFAULT_SUMMARY_BUDGET_TOKENS,
    ) -> None:
        self._llm = llm
        self._cache = cache
        self._glossary = glossary
        self._telemetry = telemetry
        self._validator = validator or ReadabilityValidator()
        self._budget_tokens = budget_tokens

    def summarize(self, paper_text: PaperText, mode: Persona) -> SummaryResult:
        started = time.perf_counter()
        key = f"summary:{paper_text.paper_id}:{mode}"
        cached = self._cache.get(key)
        if cached is not None:
            result = SummaryResult.model_validate_json(cached)
            self._record_summary(started, mode, cache_hit=True)
            return result

        compressed = _compress_paper_text(paper_text)
        hits = glossary_hits(paper_text.plain_text(), self._glossary)
        completion = self._llm.complete(
            build_summary_prompt(paper_text, mode, hits, compressed),
            persona=mode,
            budget_tokens=self._budget_tokens,
        )
        sections = _parse_summary_sections(completion.text)
        if mode == "undergrad":
            sections = _add_undergrad_aids(sections, paper_text.plain_text())
        result = SummaryResult(
            paper_id=paper_text.paper_id,
            mode=mode,
            sections=sections,
            vocab_explanations=hits,
            cost=UsageCost(tokens_in=completion.tokens_in, tokens_out=completion.tokens_out),
        )
        report = self._validator.validate(result.sections.combined_text(), mode)
        if mode == "undergrad" and not report.passed:
            retry_completion = self._llm.complete(
                build_summary_prompt(paper_text, mode, hits, compressed)
                + "\n문장을 더 짧게 다시 작성하라.",
                persona=mode,
                budget_tokens=self._budget_tokens,
            )
            result.sections = _add_undergrad_aids(
                _parse_summary_sections(retry_completion.text),
                paper_text.plain_text(),
            )
            result.cost.tokens_in += retry_completion.tokens_in
            result.cost.tokens_out += retry_completion.tokens_out
            self._validator.validate(result.sections.combined_text(), mode)

        self._cache.set(key, result.model_dump_json().encode(), SUMMARY_TTL_SECONDS)
        self._record_summary(
            started,
            mode,
            cache_hit=False,
            tokens_in=result.cost.tokens_in,
            tokens_out=result.cost.tokens_out,
        )
        return result

    def _record_summary(
        self,
        started: float,
        mode: Persona,
        cache_hit: bool,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        self._telemetry.record(
            TelemetryEvent(
                op="summarize",
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cache_hit=cache_hit,
                persona=mode,
            )
        )


def _compress_paper_text(paper_text: PaperText) -> str:
    chunks: list[str] = []
    for section in paper_text.sections:
        chunks.append(f"[{section.title}]\n{section.text.strip()}")
    text = "\n\n".join(chunks)
    if len(text) <= MAX_COMPRESSED_CHARS:
        return text
    head = text[: MAX_COMPRESSED_CHARS // 2]
    tail = text[-MAX_COMPRESSED_CHARS // 2 :]
    return f"{head}\n\n[중간 본문 압축 생략]\n\n{tail}"


def _parse_summary_sections(text: str) -> SummarySections:
    labels = {
        "question": r"(?:연구\s*질문|질문)",
        "method": r"방법",
        "result": r"결과",
        "limit": r"한계",
    }
    extracted: dict[str, str] = {}
    positions: list[tuple[str, int, int]] = []
    for key, pattern in labels.items():
        match = re.search(pattern + r"\s*[:：]", text)
        if match:
            positions.append((key, match.start(), match.end()))
    positions.sort(key=lambda item: item[1])
    for idx, (key, _start, content_start) in enumerate(positions):
        content_end = positions[idx + 1][1] if idx + 1 < len(positions) else len(text)
        extracted[key] = text[content_start:content_end].strip()
    if set(extracted) >= set(labels):
        return SummarySections(
            question=extracted["question"],
            method=extracted["method"],
            result=extracted["result"],
            limit=extracted["limit"],
        )
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。？！])\s+", text) if s.strip()]
    while len(sentences) < 4:
        sentences.append(text.strip())
    return SummarySections(
        question=sentences[0],
        method=sentences[1],
        result=sentences[2],
        limit=sentences[3],
    )


def _add_undergrad_aids(sections: SummarySections, source_text: str) -> SummarySections:
    acronyms = sorted(set(re.findall(r"\b[A-Z]{2,}\b", source_text)))
    formulas = re.findall(r"[$][^$]{2,80}[$]|[A-Za-z]\s*=\s*[^.;,\n]{1,80}", source_text)
    if acronyms and not any(acronym in sections.question for acronym in acronyms):
        sections.question += f" 약어 풀이: {acronyms[0]}는 본문에 처음 나온 핵심 약어입니다."
    if formulas:
        sections.method += f" 수식 해석: {formulas[0].strip('$')}는 입력과 출력의 관계를 간단히 나타낸 식입니다."
    return sections
