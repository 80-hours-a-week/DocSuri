"""Property-based tests (Hypothesis) — PBT-S1~S5 (business-rules.md §2)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from summarization.domain.cache_key import build_cache_key
from summarization.domain.glossary import GlossaryResolver
from summarization.domain.models import (
    Glossary,
    Persona,
    SummaryRequest,
    SummaryResultDTO,
    Task,
    TermMapping,
    TranslationDraft,
)
from summarization.domain.refiner import InputRefiner

_text = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=0, max_size=400
)


# PBT-S1 — cache key determinism / immutable identity.
@given(
    paper=st.text(min_size=1, max_size=20),
    version=st.integers(min_value=1, max_value=99),
    task=st.sampled_from(list(Task)),
    persona=st.sampled_from(list(Persona)),
    gver=st.integers(min_value=0, max_value=50),
)
def test_pbt_cache_key_deterministic(paper, version, task, persona, gver) -> None:
    req = SummaryRequest(paper_id=paper, version=version, task=task, persona=persona)
    a = build_cache_key(req, glossary_ver=gver, model_ver="m")
    b = build_cache_key(req, glossary_ver=gver, model_ver="m")
    assert a == b
    assert a.object_path() == b.object_path()


# PBT-S2 — refine is a fixed point on already-refined body.
@given(raw=_text.map(lambda s: s + "\n"))
def test_pbt_refine_idempotent(raw: str) -> None:
    once = InputRefiner().refine(raw).body
    twice = InputRefiner().refine(once).body
    assert once == twice


# PBT-S3 — post-substitution idempotent; keep-as-is words never altered.
@given(text=_text)
def test_pbt_post_substitution_idempotent(text: str) -> None:
    glossary = Glossary(user_overrides=(TermMapping("주의", "어텐션", prompt_enforced=False),))
    once = GlossaryResolver.post_substitute(text, glossary)
    twice = GlossaryResolver.post_substitute(once, glossary)
    assert once == twice


@given(text=_text)
def test_pbt_keep_as_is_invariant(text: str) -> None:
    # An empty user glossary must never change the text (keep-as-is is prompt-side, not post-sub).
    assert GlossaryResolver.post_substitute(text, Glossary()) == text


# PBT-S4 — response to_dict round-trip exposes no internal fields (SEC-9).
@given(korean=_text)
def test_pbt_response_to_dict_sec9(korean: str) -> None:
    dto = SummaryResultDTO(
        task=Task.TRANSLATE,
        translation=TranslationDraft(korean_text=korean, kept_terms=("BERT",)),
        meta={"source": "abstract"},
    )
    out = dto.to_dict()
    flat = str(out)
    for forbidden in ("model_ver", "prompt_ver", "cost", "token", "redis", "cache_key"):
        assert forbidden not in flat
    assert out["status"] == "ok"
