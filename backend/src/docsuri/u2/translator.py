"""Selection-based paragraph translation for U2."""

from __future__ import annotations

import time

from docsuri.u0.ports import Glossary, LlmPort, Telemetry, TelemetryEvent

from .glossary_tools import glossary_hits
from .models import InputMode, TranslationResult, TranslationSelection
from .prompts import build_translation_prompt

DEFAULT_TRANSLATION_BUDGET_TOKENS = 800


class SelectionTranslator:
    def __init__(
        self,
        llm: LlmPort,
        glossary: Glossary,
        telemetry: Telemetry,
        budget_tokens: int = DEFAULT_TRANSLATION_BUDGET_TOKENS,
    ) -> None:
        self._llm = llm
        self._glossary = glossary
        self._telemetry = telemetry
        self._budget_tokens = budget_tokens

    def select(
        self,
        source_text: str,
        start: int,
        end: int,
        input_mode: InputMode,
        long_press_ms: int | None = None,
    ) -> TranslationSelection:
        if input_mode == "mobile" and (long_press_ms is None or long_press_ms < 500):
            raise ValueError("모바일 선택은 500ms 이상 롱프레스가 필요합니다.")
        if start < 0 or end <= start or end > len(source_text):
            raise ValueError("선택 범위가 올바르지 않습니다.")
        return TranslationSelection(
            source_excerpt=source_text[start:end].strip(),
            input_mode=input_mode,
        )

    def translate(self, selection: TranslationSelection) -> TranslationResult:
        started = time.perf_counter()
        hits = glossary_hits(selection.source_excerpt, self._glossary)
        completion = self._llm.complete(
            build_translation_prompt(selection.source_excerpt, hits),
            persona="undergrad",
            budget_tokens=self._budget_tokens,
        )
        self._telemetry.record(
            TelemetryEvent(
                op="translate",
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                cache_hit=False,
                persona="undergrad",
            )
        )
        return TranslationResult(
            source_excerpt=selection.source_excerpt,
            target_text=completion.text,
            glossary_hits=hits,
        )
