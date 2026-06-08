"""Summarization presets (AGENTS.md §6.4 length cap).

12 combos: 3 length × 4 angle. Each `LengthPreset` carries a token cap
that maps to the post-trimmer in `service.py`. Each `AnglePreset`
inflects the prompt; the per-angle prompt overlay lives in `prompts.py`.
"""

from __future__ import annotations

from enum import Enum


class LengthPreset(str, Enum):
    """AGENTS.md §6.4 — TL;DR / 문단 / 페이지."""

    TLDR = "tldr"            # 1 sentence
    PARAGRAPH = "paragraph"  # 150-200 chars Korean
    PAGE = "page"            # 800-1200 chars Korean

    @property
    def max_tokens(self) -> int:
        # Generous output caps; the post-trimmer also enforces char limits.
        # Sized for §6.5 JSON envelope around Korean content. Korean chars
        # cost ~1.5 tokens each; envelope adds ~60 tokens; we want headroom
        # so the response is never truncated mid-JSON (the parser has a
        # rescue path, but full JSON is cleaner for the demo).
        return {
            LengthPreset.TLDR: 300,
            LengthPreset.PARAGRAPH: 800,
            LengthPreset.PAGE: 2400,
        }[self]

    @property
    def char_cap(self) -> int:
        return {
            LengthPreset.TLDR: 80,
            LengthPreset.PARAGRAPH: 220,
            LengthPreset.PAGE: 1200,
        }[self]


class AnglePreset(str, Enum):
    """기여 / 방법 / 결과 / 비판."""

    CONTRIBUTION = "contribution"
    METHOD = "method"
    RESULT = "result"
    CRITICAL = "critical"

    @property
    def korean_label(self) -> str:
        return {
            AnglePreset.CONTRIBUTION: "기여 중심",
            AnglePreset.METHOD: "방법 중심",
            AnglePreset.RESULT: "결과·실험 중심",
            AnglePreset.CRITICAL: "비판적 검토",
        }[self]


# Sanity assertion — 3 × 4 = 12 combos.
assert len(LengthPreset) * len(AnglePreset) == 12, "preset matrix must be 12"
