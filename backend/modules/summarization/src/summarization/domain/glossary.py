"""GlossaryResolver — seed (P1) ∪ personal (P2) with two application paths (BR-S4 / Q8).

핵심 용어 보존은 프롬프트 단계에서 강제하고(keep-as-is + core mappings → prompt),
후치환은 사용자 선호 용어에 한정하여 단순 명사를 교정한다(deterministic post-substitution,
no LLM re-call). Post-substitution is restricted to simple nouns so Korean particle
attachment ("어텐션을/어텐션이") stays safe.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Sequence

from ..ports.ports import GlossaryRepositoryPort
from .models import Glossary, TermMapping

# P1 seed: model/abbreviation names kept in English (keep-as-is) — biggest cheap win (§9.1).
SEED_KEEP_AS_IS: tuple[str, ...] = (
    "Transformer", "BERT", "GPT", "LoRA", "RAG", "LLM", "CNN", "RNN", "LSTM", "ViT",
    "ResNet", "ImageNet", "SOTA", "MLP", "GAN", "VAE", "ReLU", "Adam", "SGD",
)

# P1 seed: core domain mappings enforced in the prompt for consistency.
SEED_MAPPINGS: tuple[TermMapping, ...] = (
    TermMapping("attention", "어텐션", prompt_enforced=True),
    TermMapping("embedding", "임베딩", prompt_enforced=True),
    TermMapping("fine-tuning", "파인튜닝", prompt_enforced=True),
    TermMapping("latent space", "잠재 공간", prompt_enforced=True),
)


def _seed_signature() -> str:
    """Short content hash of the shared seed glossary (keep-as-is + prompt-enforced mappings).

    The seed rides into every summary/translate prompt, so it is part of the derived artifact's
    identity — editing it changes the base output. Folding this hash into the cache path makes a
    seed edit self-invalidate (new path → miss → regenerate) with no manual version bump."""
    payload = (
        tuple(SEED_KEEP_AS_IS),
        tuple((m.term_from, m.term_to, m.prompt_enforced) for m in SEED_MAPPINGS),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:8]


SEED_VER = _seed_signature()

# Frozen marker of the seed shipped when the cache-key seed dimension was introduced. The seed
# segment is OMITTED from the cache path while ``SEED_VER`` equals this, so existing summary/
# translate objects stay valid on deploy (no gratuitous cache-wide regeneration). Editing the seed
# above changes ``SEED_VER`` → the segment appears → exactly the affected objects invalidate.
# NEVER update this literal to match a seed edit — doing so would defeat the invalidation.
_SEED_BASELINE_VER = "344c3ccb"


def seed_cache_segment() -> str:
    """Cache-path seed segment: empty while the seed matches the shipped baseline, else the
    current ``SEED_VER`` (so the path changes only when the seed actually changes)."""
    return "" if SEED_VER == _SEED_BASELINE_VER else SEED_VER


logger = logging.getLogger(__name__)


class GlossaryResolver:
    def __init__(self, repo: GlossaryRepositoryPort | None = None) -> None:
        self._repo = repo

    def resolve(self, user_id: str | None) -> Glossary:
        overrides: Sequence[TermMapping] = ()
        if self._repo is not None and user_id is not None:
            try:
                overrides = tuple(self._repo.get_user_glossary(user_id))
            except Exception:  # noqa: BLE001 — personal-term overrides are OPTIONAL; a repo fault
                # (DB unavailable, table not yet migrated) must not abstain the whole summary/
                # translate. Degrade to the shared seed glossary (no personal terms).
                logger.warning(
                    "personal glossary lookup failed — degrading to seed-only", exc_info=True
                )
                overrides = ()
        return Glossary(
            seed_mappings=SEED_MAPPINGS,
            keep_as_is=SEED_KEEP_AS_IS,
            user_overrides=tuple(overrides),
        )

    @staticmethod
    def signature_of(glossary: Glossary) -> int:
        """Stable CONTENT identity of the user's PROMPT-ENFORCED override terms (0 = none), from an
        already-resolved ``Glossary`` (pure — no I/O). This is the cache identity for BOTH tasks:
        the derived artifact varies only with prompt-enforced terms (they ride into the prompt),
        while post-substitution (weak) terms are applied as a read-time overlay on a SHARED base,
        so a weak-only edit must NOT fork the cache (NFR-C1).

        It is a content HASH, not a counter: a filtered ``MAX(glossary_ver) WHERE prompt_enforced``
        is non-monotonic — demoting the max prompt-enforced term to post-substitution leaves the
        value unchanged, so a stale artifact would be served (BR-S1 invalidation miss). The hash
        changes whenever the prompt-enforced set is added to / edited / demoted, and is unchanged
        by post-substitution-only edits."""
        enforced = sorted(
            (m.term_from, m.term_to) for m in glossary.user_overrides if m.prompt_enforced
        )
        if not enforced:
            return 0
        digest = hashlib.sha256(repr(enforced).encode("utf-8")).hexdigest()
        # Positive content id; 0 is reserved above for "no prompt-enforced terms" (shared baseline).
        return int(digest[:12], 16)

    def prompt_glossary_signature(self, user_id: str | None) -> int:
        """Convenience: resolve the user's glossary and return its prompt-enforced content
        signature (see [[signature_of]]). Degrades to baseline (0) on a repo fault via
        [[resolve]]."""
        return self.signature_of(self.resolve(user_id))

    def list_user_terms(self, user_id: str) -> Sequence[TermMapping]:
        """Return the user's personal term overrides (owner-scoped, SEC-8). Empty when no
        repository is configured — used to pre-fill the badge editor (read-only)."""
        if self._repo is None:
            return ()
        return tuple(self._repo.get_user_glossary(user_id))

    def upsert_term(
        self, user_id: str, term_from: str, term_to: str, *, prompt_enforced: bool = False
    ) -> int:
        """Persist a personal term override (owner-scoped, SEC-8); return the bumped
        ``glossary_ver``. Phase 1 default ``prompt_enforced=False`` → simple-noun
        post-substitution (translation only). Raises when no repository is configured."""
        if self._repo is None:
            raise RuntimeError("glossary repository is not configured")
        return self._repo.upsert_term(
            user_id, term_from, term_to, prompt_enforced=prompt_enforced
        )

    @staticmethod
    def post_substitute(text: str, glossary: Glossary) -> str:
        """Deterministic post-substitution for user-preference simple nouns (no LLM re-call).

        Only ``prompt_enforced=False`` overrides are applied here (simple noun swaps);
        whole-word, longest-first to avoid partial overlaps. Idempotent (PBT-S3).
        """
        post = [m for m in glossary.user_overrides if not m.prompt_enforced]
        for m in sorted(post, key=lambda x: len(x.term_from), reverse=True):
            # Leading boundary only: Korean attaches particles directly to the noun
            # ("어텐션을/어텐션이"), so a trailing ``(?!\w)`` would block the swap. Matching at a
            # left boundary replaces just the noun and leaves the particle intact (particle-safe).
            # The replacement is a function (not a string) so a user-supplied ``term_to`` is
            # inserted literally — backslash sequences (e.g. ``\g<0>``) are NOT interpreted as
            # regex backreferences (input-injection safe now that term_to is user-writable).
            text = re.sub(
                rf"(?<!\w){re.escape(m.term_from)}", lambda _match, repl=m.term_to: repl, text
            )
        return text
