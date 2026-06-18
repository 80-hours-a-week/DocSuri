"""GlossaryResolver — seed (P1) ∪ personal (P2) with two application paths (BR-S4 / Q8).

핵심 용어 보존은 프롬프트 단계에서 강제하고(keep-as-is + core mappings → prompt),
후치환은 사용자 선호 용어에 한정하여 단순 명사를 교정한다(deterministic post-substitution,
no LLM re-call). Post-substitution is restricted to simple nouns so Korean particle
attachment ("어텐션을/어텐션이") stays safe.
"""

from __future__ import annotations

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


class GlossaryResolver:
    def __init__(self, repo: GlossaryRepositoryPort | None = None) -> None:
        self._repo = repo

    def resolve(self, user_id: str | None) -> Glossary:
        overrides: Sequence[TermMapping] = ()
        if self._repo is not None and user_id is not None:
            overrides = tuple(self._repo.get_user_glossary(user_id))
        return Glossary(
            seed_mappings=SEED_MAPPINGS,
            keep_as_is=SEED_KEEP_AS_IS,
            user_overrides=tuple(overrides),
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
            text = re.sub(rf"(?<!\w){re.escape(m.term_from)}", m.term_to, text)
        return text
