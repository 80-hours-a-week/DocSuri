"""Cache-key derivation for LLM prompt cache.

AGENTS.md §4.1 — `infra/llm` is the sole owner of cache key derivation.
Domain modules must never compute one. The key is shaped so that two
requests sharing the same system blocks (§6 conventions, paper text,
glossary) collide on cache regardless of the fresh user_message — that
is the whole point of Anthropic `cache_control: ephemeral`.
"""

from __future__ import annotations

import hashlib

from app.infra.llm.protocol import LLMRequest


def derive_cache_key(req: LLMRequest) -> str:
    """Derive a stable cache key for the cached portion of `req`.

    Key composition (intentionally excludes `user_message`):
      sha256( model_label || "\\0" ||
              join(block.name) || "\\0" ||
              join(block.text) )

    `model_label` is taken from `purpose` because the adapter picks the
    concrete model from purpose (Sonnet for summary/translation, Haiku
    for verify/normalize). This keeps the key stable across mock vs live.
    """

    hasher = hashlib.sha256()
    hasher.update(req.purpose.encode("utf-8"))
    hasher.update(b"\0")
    for block in req.system_blocks:
        hasher.update(block.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(block.text.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()
