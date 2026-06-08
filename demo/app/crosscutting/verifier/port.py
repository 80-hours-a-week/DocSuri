"""Sentence-level entailment verifier port (AGENTS.md §4.3).

Sprint 1 stub: always returns SUPPORTED. Sprint 2 will plug in the real
Claude-Haiku 4-way classifier. Domain modules import this Protocol only —
they MUST NOT call any verifier implementation directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.papers.models import VerifyLabel


@dataclass
class VerifyResult:
    label: VerifyLabel
    confidence: float


class VerifierPort(Protocol):
    async def verify(self, sentence: str, evidence_spans: list[str]) -> VerifyResult:
        ...


class AlwaysSupportedVerifier:
    """Sprint 1 walking-skeleton stub. Replaced in Sprint 2."""

    async def verify(self, sentence: str, evidence_spans: list[str]) -> VerifyResult:
        # Trivial heuristic so the badge shows variation in the UI demo:
        # if no evidence given, label as NOT_FOUND so the UI can show all 4 colours.
        if not evidence_spans:
            return VerifyResult(label="NOT_FOUND", confidence=0.5)
        return VerifyResult(label="SUPPORTED", confidence=0.95)
