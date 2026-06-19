"""Cache-key construction — immutable identity (§11 / BR-S1 / INV-5).

Identity = (paper, version, task, lang, persona, glossaryVer, modelVer, promptVer). The
personal glossary version folds per-user personalization into the shared key space (Q7),
so no separate ``userId`` is needed. Same key ⇒ same artifact, forever.
"""

from __future__ import annotations

from .models import Scope, SummaryCacheKey, SummaryRequest, Task

# Prompt template version — bump to invalidate all derived objects (key changes).
PROMPT_VER = "p1"


def build_cache_key(
    request: SummaryRequest, *, glossary_ver: int, model_ver: str
) -> SummaryCacheKey:
    # Identity dimensions (§11): summary varies by persona (2 variants), scope fixed to
    # full; translate varies by scope (abstract|full), persona-agnostic (single).
    scope = Scope.FULL if request.task == Task.SUMMARY else request.scope
    return SummaryCacheKey(
        paper_id=request.paper_id,
        version=request.version,
        task=request.task,
        target_lang=request.target_lang,
        scope=scope,
        persona=request.persona,
        glossary_ver=glossary_ver,
        model_ver=model_ver,
        prompt_ver=PROMPT_VER,
    )
