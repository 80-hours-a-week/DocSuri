"""Personal-glossary redesign — shared base translation + read-time weak-term overlay + seed
cache-invalidation (BR-S1/BR-S4/NFR-C1).

Translate caches ONE shared base per paper (keyed on the prompt-enforced signature); the user's
weak (post-substitution) terms are applied on read. So a weak-only edit — or two users with
different weak sets — must NOT fork the cache into an identical re-generation, and a seed edit
must self-invalidate the path.
"""

from __future__ import annotations

import json

from summarization.domain import glossary as glossary_mod
from summarization.domain.assembler import ResultAssembler
from summarization.domain.cache_key import build_cache_key
from summarization.domain.glossary import GlossaryResolver
from summarization.domain.models import (
    AuthSession,
    Glossary,
    RequestContext,
    SourceKind,
    SourceText,
    SummaryRequest,
    Task,
    TermMapping,
    TranslationDraft,
)
from tests.stubs import StubStore, make_orchestrator, tiny_doc


class _FakeGlossaryRepo:
    """Owner-scoped term store whose per-user term set can be swapped mid-test (edit simulation)."""

    def __init__(self, terms_by_user: dict[str, tuple[TermMapping, ...]]) -> None:
        self.terms_by_user = terms_by_user

    def get_user_glossary(self, user_id: str):
        return self.terms_by_user.get(user_id, ())

    def upsert_term(self, user_id, term_from, term_to, *, prompt_enforced) -> int:  # unused here
        return 1


def _ctx(user: str = "u1") -> RequestContext:
    return RequestContext(auth_session=AuthSession(user_id=user), request_id="r")


def _translate_req() -> SummaryRequest:
    return SummaryRequest(paper_id="2401.1", version=1, task=Task.TRANSLATE,
                          abstract="An abstract about BERT.")


def _text(result) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False)


def _weak(term_from: str, term_to: str) -> TermMapping:
    return TermMapping(term_from, term_to, prompt_enforced=False)


def _orch(store: StubStore, terms_by_user: dict[str, tuple[TermMapping, ...]]):
    resolver = GlossaryResolver(_FakeGlossaryRepo(terms_by_user))
    return make_orchestrator(store=store, glossary_resolver=resolver)


# --- orchestrator: shared base, weak overlay on read ------------------------------------


def test_weak_terms_share_one_base_across_users() -> None:
    # Two users with DIFFERENT weak terms → identical prompt-enforced signature (0) → same shared
    # base key (no owner segment). The second user is a cache HIT (no re-translation), yet each
    # user sees their OWN weak overlay applied on read (NFR-C1: one base, per-user views).
    store = StubStore()
    orch = _orch(store, {
        "u1": (_weak("BERT", "버트"),),
        "u2": (_weak("BERT", "베르트"),),
    })
    r1 = orch.run(_translate_req(), _ctx("u1"))
    r2 = orch.run(_translate_req(), _ctx("u2"))

    assert store.puts == 1  # ONE shared base — u2 hit u1's base, no second generation
    assert r2.to_dict()["cached"] is True
    assert "버트" in _text(r1) and "베르트" not in _text(r1)  # u1's overlay
    assert "베르트" in _text(r2) and "버트" not in _text(r2)  # u2's overlay


def test_weak_edit_reflected_on_read_without_retranslation() -> None:
    # Editing a weak term does not change the cache key → HIT → the new term is applied by the
    # read-time overlay (no re-translation, no per-user fork). This is the core cost win.
    store = StubStore()
    terms: dict[str, tuple[TermMapping, ...]] = {"u1": (_weak("BERT", "버트"),)}
    orch = _orch(store, terms)

    r1 = orch.run(_translate_req(), _ctx())
    assert store.puts == 1 and "버트" in _text(r1)

    terms["u1"] = (_weak("BERT", "베르트"),)  # user edits the preferred term
    r2 = orch.run(_translate_req(), _ctx())
    assert store.puts == 1  # NO re-translation — same key, cache HIT
    assert r2.to_dict()["cached"] is True
    assert "베르트" in _text(r2) and "버트" not in _text(r2)  # edit reflected on read


def test_hit_and_miss_views_match_for_same_user() -> None:
    # The fresh (write-through) view and the cache-hit view are identical except for ``cached``.
    store = StubStore()
    orch = _orch(store, {"u1": (_weak("BERT", "버트"),)})
    miss = orch.run(_translate_req(), _ctx()).to_dict()
    hit = orch.run(_translate_req(), _ctx()).to_dict()
    assert miss["cached"] is False and hit["cached"] is True
    assert {k: v for k, v in miss.items() if k != "cached"} == {
        k: v for k, v in hit.items() if k != "cached"
    }


def test_stored_base_is_shared_and_weak_free() -> None:
    # What lands in the store is the BASE (no weak substitution baked in), so it is reusable across
    # users. The overlay happens only on the returned view, not on the cached object.
    store = StubStore()
    orch = _orch(store, {"u1": (_weak("BERT", "버트"),)})
    orch.run(_translate_req(), _ctx())
    (stored,) = store.data.values()
    assert "BERT" in json.dumps(stored, ensure_ascii=False)  # base keeps the un-substituted term
    assert "버트" not in json.dumps(stored, ensure_ascii=False)


# --- assembler: base assembly (no post-sub) + read-time overlay -------------------------


def _src() -> SourceText:
    return SourceText(kind=SourceKind.ABSTRACT)


def test_assemble_translation_does_not_post_substitute() -> None:
    # Regression: post-substitution used to be baked into assemble_translation; it is now a
    # read-time overlay, so the assembled base must keep weak term_from text verbatim.
    draft = TranslationDraft(doc_model=tiny_doc(paragraph="This uses BERT."), kept_terms=())
    base = ResultAssembler().assemble_translation(draft, _src()).to_dict()
    assert base["translation"]["docModel"]["sections"][0]["blocks"][0]["text"] == "This uses BERT."


def test_overlay_applies_weak_terms_and_reprojects_fulltext() -> None:
    doc = tiny_doc(title="BERT 소개", paragraph="이것은 BERT 이다.")
    draft = TranslationDraft(doc, kept_terms=())
    base = ResultAssembler().assemble_translation(draft, _src()).to_dict()
    glossary = Glossary(user_overrides=(_weak("BERT", "버트"),))

    view = ResultAssembler.overlay_translation(base, glossary)
    section = view["translation"]["docModel"]["sections"][0]
    assert section["title"] == "버트 소개"
    assert section["blocks"][0]["text"] == "이것은 버트 이다."
    # fullText re-projected from the substituted sections (stays aligned).
    assert "버트" in view["translation"]["docModel"]["fullText"]
    assert "BERT" not in view["translation"]["docModel"]["fullText"]
    # Base object left untouched (overlay works on a copy).
    assert "BERT" in base["translation"]["docModel"]["sections"][0]["title"]


def test_overlay_is_noop_without_weak_terms() -> None:
    draft = TranslationDraft(doc_model=tiny_doc(paragraph="This uses BERT."), kept_terms=())
    base = ResultAssembler().assemble_translation(draft, _src()).to_dict()
    # No weak terms (seed-only) → returns the SAME object, no copy/work.
    assert ResultAssembler.overlay_translation(base, Glossary()) is base


# --- seed change → cache self-invalidation ----------------------------------------------


def test_current_seed_omits_cache_segment() -> None:
    # The shipped seed matches the frozen baseline → segment omitted → existing cache paths
    # unchanged on deploy (no gratuitous regeneration).
    assert glossary_mod.seed_cache_segment() == ""


def test_seed_edit_flips_segment_and_changes_path(monkeypatch) -> None:
    req = _translate_req()
    k_base = build_cache_key(req, glossary_ver=0, model_ver="m", user_id="u1", seed_ver="")
    assert "_s" not in k_base.object_path()

    monkeypatch.setattr(glossary_mod, "SEED_VER", "deadbeef")
    assert glossary_mod.seed_cache_segment() == "deadbeef"
    k_seed = build_cache_key(
        req, glossary_ver=0, model_ver="m", user_id="u1", seed_ver=glossary_mod.seed_cache_segment()
    )
    assert "_sdeadbeef" in k_seed.object_path()
    assert k_seed.object_path() != k_base.object_path()  # seed edit → new key → miss → regenerate
