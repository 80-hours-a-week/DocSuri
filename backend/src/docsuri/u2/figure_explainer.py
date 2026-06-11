"""Figure/table caption explainer for U2."""

from __future__ import annotations

import re
import time

from docsuri.u0.ports import LlmPort, Telemetry, TelemetryEvent

from .models import FigureContext
from .prompts import build_figure_prompt

DEFAULT_FIGURE_BUDGET_TOKENS = 300


class FigureExplainer:
    def __init__(
        self,
        llm: LlmPort,
        telemetry: Telemetry,
        budget_tokens: int = DEFAULT_FIGURE_BUDGET_TOKENS,
    ) -> None:
        self._llm = llm
        self._telemetry = telemetry
        self._budget_tokens = budget_tokens

    def explain(self, figure: FigureContext) -> str:
        if figure.touch_target_width_css_px < 44 or figure.touch_target_height_css_px < 44:
            raise ValueError("그림 영역의 터치 타깃은 44 CSS px 이상이어야 합니다.")
        started = time.perf_counter()
        completion = self._llm.complete(
            build_figure_prompt(figure.caption, figure.context),
            persona="undergrad",
            budget_tokens=self._budget_tokens,
        )
        self._telemetry.record(
            TelemetryEvent(
                op="figure_explain",
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                cache_hit=False,
                persona="undergrad",
            )
        )
        return _first_two_sentences(completion.text)


def _first_two_sentences(text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。？！])\s+", text) if s.strip()]
    return " ".join(sentences[:2]) if sentences else text.strip()
