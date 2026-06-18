"""ResultAssembler — assemble + SEC-9 filter + post-substitution (BR-S9 / BR-S14).

Builds the terminal ``SummaryResultDTO`` from a grounded draft. SEC-9 exposure control
lives in ``SummaryResultDTO.to_dict`` (no tokens/cost/cache-key/model id). User-preference
simple-noun post-substitution is applied to translation text here (Q8).
"""

from __future__ import annotations

from .glossary import GlossaryResolver
from .models import (
    Glossary,
    SourceText,
    SummaryDraft,
    SummaryResultDTO,
    Task,
    TranslationDraft,
)


class ResultAssembler:
    def assemble_summary(self, draft: SummaryDraft, source: SourceText) -> SummaryResultDTO:
        meta = {"source": str(source.kind)}
        if source.fallback_reason:
            meta["fallback"] = source.fallback_reason  # honest "abstract-based summary" note
        return SummaryResultDTO(task=Task.SUMMARY, summary=draft, meta=meta)

    def assemble_translation(
        self, draft: TranslationDraft, glossary: Glossary
    ) -> SummaryResultDTO:
        # Deterministic post-substitution for user-preference simple nouns (no LLM re-call).
        text = GlossaryResolver.post_substitute(draft.korean_text, glossary)
        final = TranslationDraft(korean_text=text, kept_terms=draft.kept_terms)
        return SummaryResultDTO(task=Task.TRANSLATE, translation=final, meta={"source": "abstract"})
