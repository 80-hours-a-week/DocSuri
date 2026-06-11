"""Readability validation for U2 persona outputs."""

from __future__ import annotations

import re

from docsuri.u0.ports import Persona

from .models import ReadabilityMetrics, ReadabilityReport

MAX_UNDERGRAD_AVG_EOJEOL = 22
MAX_UNDERGRAD_DIFFICULT_TOKENS = 8

DIFFICULT_KO_TERMS = {
    "retrieval-augmented",
    "generation",
    "transformer",
    "attention",
    "benchmark",
    "baseline",
    "semantic",
    "similarity",
    "hallucination",
    "inference",
}


class ReadabilityValidator:
    """Local post-check for NFR-UX-01/02.

    MVP keeps the metric intentionally transparent: sentence count and average
    Korean eojeol-like whitespace tokens. A richer KKL vocabulary checker can
    replace this without changing U2 DTOs.
    """

    def validate(self, text: str, mode: Persona) -> ReadabilityReport:
        counts = [_eojeol_count(sentence) for sentence in _sentences(text)]
        if not counts:
            counts = [0]
        average = round(sum(counts) / len(counts), 2)
        metrics = ReadabilityMetrics(
            sentence_count=len(counts),
            average_eojeol_per_sentence=average,
            max_eojeol_per_sentence=max(counts),
            difficult_token_count=_difficult_token_count(text),
        )
        issues: list[str] = []
        if mode == "undergrad" and average > MAX_UNDERGRAD_AVG_EOJEOL:
            issues.append(
                f"학부 모드 평균 문장 길이 {average}어절이 기준 "
                f"{MAX_UNDERGRAD_AVG_EOJEOL}어절을 초과했습니다."
            )
        if (
            mode == "undergrad"
            and metrics.difficult_token_count > MAX_UNDERGRAD_DIFFICULT_TOKENS
        ):
            issues.append(
                "학부 모드에 풀이 없는 어려운 영어/학술 토큰이 "
                f"{metrics.difficult_token_count}개 포함되었습니다."
            )
        return ReadabilityReport(mode=mode, passed=not issues, metrics=metrics, issues=issues)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?。？！\n]+", text) if s.strip()]


def _eojeol_count(sentence: str) -> int:
    return len([token for token in re.split(r"\s+", sentence.strip()) if token])


def _difficult_token_count(text: str) -> int:
    lowered = text.lower()
    terms = {term for term in DIFFICULT_KO_TERMS if term in lowered}
    uppercase = set(re.findall(r"\b[A-Z]{2,}\b", text))
    long_english = {
        token.lower()
        for token in re.findall(r"\b[A-Za-z][A-Za-z-]{10,}\b", text)
        if token.lower() not in {"additional"}
    }
    return len(terms | uppercase | long_english)
