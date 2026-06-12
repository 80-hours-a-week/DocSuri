"""Persona-aware paper summary engine for U2."""

from __future__ import annotations

import re
import time

from docsuri.u0.ports import CachePort, Glossary, LlmPort, Persona, Telemetry, TelemetryEvent

from .glossary_tools import glossary_hits
from .models import PaperText, ReadabilityReport, SummaryResult, SummarySections, UsageCost
from .prompts import build_summary_prompt
from .readability import ReadabilityValidator

SUMMARY_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_SUMMARY_BUDGET_TOKENS = 1200
MAX_COMPRESSED_CHARS = 10_000
ACRONYM_EXPLANATIONS = {
    "AI": "인공지능",
    "CNN": "합성곱 신경망",
    "LLM": "대규모 언어 모델",
    "MLM": "마스크 언어 모델",
    "NLP": "자연어 처리",
    "RAG": "검색 증강 생성",
    "RNN": "순환 신경망",
}


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
        self.last_readability_report: ReadabilityReport | None = None

    def summarize(self, paper_text: PaperText, mode: Persona) -> SummaryResult:
        started = time.perf_counter()
        key = f"summary:{paper_text.paper_id}:{mode}"
        cached = self._cache.get(key)
        if cached is not None:
            result = SummaryResult.model_validate_json(cached)
            self._record_summary(started, mode, cache_hit=True)
            return result

        compressed = _compress_paper_text(paper_text)
        hits = glossary_hits(compressed, self._glossary)
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
        self.last_readability_report = report
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
            report = self._validator.validate(result.sections.combined_text(), mode)
            self.last_readability_report = report

        if report.passed:
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
        # 두 형식 인식: ① 인라인 라벨("연구 질문: …") ② 마크다운 헤딩 라인
        # ("## 연구 질문") — 실 LLM(Haiku) 검증에서 ②로 응답해 fallback으로
        # 빠지며 섹션이 밀리던 결함 보강 (2026-06-12, 실모델 정합).
        match = re.search(pattern + r"\s*[:：]", text)
        if match is None:
            match = re.search(
                r"(?m)^[ \t]*#{1,6}[ \t]*\**" + pattern + r"\**[ \t]*$", text
            )
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
    known_acronyms = [
        f"{acronym}({ACRONYM_EXPLANATIONS[acronym]})"
        for acronym in acronyms
        if acronym in ACRONYM_EXPLANATIONS
    ]
    if known_acronyms and not any(item in sections.question for item in known_acronyms):
        sections.question += f" 약어 풀이: {', '.join(known_acronyms[:3])}."
    if formulas:
        formula = formulas[0].strip("$").strip()
        sections.method += f" 수식 해석: {formula}는 식의 왼쪽 값을 오른쪽 계산으로 얻는다는 뜻입니다."
    return sections
