"""Capability ports U7 depends on by injection (logical-components.md §2).

Dependency-isolation exceptions (RES-9 / NFR-R2 / Q1):
- ``LlmUnavailable`` — Bedrock generation failed/timed out → orchestrator abstains
  (after one retry) rather than emit ungrounded text (fail-closed, INV-4).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..domain.models import (
    Glossary,
    RefinedSource,
    SummaryCacheKey,
    SummaryDraft,
    SummaryRequest,
    TermMapping,
    TranslationDraft,
)

__all__ = [
    "LlmUnavailable",
    "LlmGatewayPort",
    "SummaryStorePort",
    "FullTextSourcePort",
    "GlossaryRepositoryPort",
]


class LlmUnavailable(Exception):
    """LLM generation dependency (Bedrock) failed — abstain after one retry (Q1/BR-S7)."""


@runtime_checkable
class LlmGatewayPort(Protocol):
    """Summary/translation generation via the LLM gateway (Bedrock, U6-gateway-fronted).

    Implementations buffer the model stream and return a complete draft so the U7
    grounding gate can validate the whole structured output before exposure (Q5/BR-S8).
    """

    def summarize(
        self, refined: RefinedSource, request: SummaryRequest, glossary: Glossary
    ) -> SummaryDraft:
        """Generate a structured summary (§3). Raises ``LlmUnavailable`` on failure."""
        ...

    def translate(
        self, abstract: str, request: SummaryRequest, glossary: Glossary
    ) -> TranslationDraft:
        """Translate the abstract to Korean. Raises ``LlmUnavailable`` on failure."""
        ...


@runtime_checkable
class SummaryStorePort(Protocol):
    """Two-tier store: read-through (Redis hot → S3 permanent), write-through (§11 / BR-S1)."""

    def get(self, key: SummaryCacheKey) -> dict | None:
        """Return the cached payload (``SummaryResultDTO.to_dict``) or None on miss."""
        ...

    def put(self, key: SummaryCacheKey, payload: dict) -> None:
        """Write-through: S3 permanent + Redis hot (immutable key, INV-5)."""
        ...


@runtime_checkable
class FullTextSourcePort(Protocol):
    """U1 full-text read capability (S3 ``stored_full_text_ref``). Read-only."""

    def get_full_text(self, paper_id: str, version: int) -> str | None:
        """Return the stored full text, or None when absent / license-disallowed (Q1)."""
        ...


@runtime_checkable
class GlossaryRepositoryPort(Protocol):
    """Personal glossary (P2) persistence — owner-scoped (SEC-8). RDS-backed."""

    def get_user_glossary(self, user_id: str) -> Sequence[TermMapping]:
        """Return the user's term overrides (owner-scoped)."""
        ...

    def get_glossary_version(self, user_id: str) -> int:
        """Return the user's current ``glossary_ver`` (0 when none → shared baseline)."""
        ...

    def upsert_term(
        self, user_id: str, term_from: str, term_to: str, *, prompt_enforced: bool
    ) -> int:
        """Add/override a personal term (owner-scoped); return the bumped ``glossary_ver``."""
        ...
