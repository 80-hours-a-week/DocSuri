"""OpenAI text-embedding-3-large adapter (infra/CLAUDE.md — 임베딩 클라이언트 규칙).

Cache key format: embed:large:{sha256(text)}
Model name is baked into the key prefix so that switching models
automatically invalidates every cached vector without a manual flush.

Dimensions: 3072 — switching to text-embedding-3-small (1536-dim) requires
an Alembic migration to resize the pgvector column and a full re-embedding.

The `openai` SDK is imported lazily inside `embed_many()` so a missing
package does not break startup (wired by container only when OPENAI_API_KEY
is set).
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072

# Key prefix encodes the model: "large" → text-embedding-3-large (3072-dim).
# Changing model → change prefix → all cached keys are automatically invalid.
_KEY_PREFIX = "embed:large"


def embedding_cache_key(text: str) -> str:
    """Derive a stable Redis cache key for the embedding of `text`.

    Pattern: embed:large:{sha256(text)}   (infra/CLAUDE.md §임베딩 클라이언트 규칙)
    Callers store/look up this key in Redis; this module never touches Redis
    directly so the TTL policy lives in the storage layer.
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}:{digest}"


@dataclass
class EmbeddingResult:
    """One embedded text. `cache_key` is ready to use as a Redis key."""

    vector: list[float]   # EMBEDDING_DIM floats
    cache_key: str        # embed:large:{sha256(text)}
    model: str            # always EMBEDDING_MODEL for this adapter


class OpenAIEmbeddingAdapter:
    """Thin async wrapper around the OpenAI Embeddings API.

    Lazy-imports `openai` to keep startup clean when the package is absent.
    Caller owns the lifecycle; call `aclose()` during application shutdown
    to release the underlying HTTP connection pool.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = None  # lazy — created on first embed_many() call

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "openai SDK not installed; add `openai>=1.0` to project dependencies."
            ) from exc
        self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text string. For multiple texts prefer `embed_many`."""
        results = await self.embed_many([text])
        return results[0]

    async def embed_many(self, texts: list[str]) -> list[EmbeddingResult]:
        """Batch-embed texts in a single API call.

        Returns results in the same order as `texts`. OpenAI guarantees
        order-preservation via the `index` field on each embedding object.
        """
        if not texts:
            return []
        client = self._ensure_client()
        logger.info("embedding.embed_many n=%d model=%s", len(texts), EMBEDDING_MODEL)
        resp = await client.embeddings.create(  # type: ignore[attr-defined]
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [
            EmbeddingResult(
                vector=item.embedding,
                cache_key=embedding_cache_key(texts[item.index]),
                model=EMBEDDING_MODEL,
            )
            for item in resp.data
        ]

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()  # type: ignore[attr-defined]
            self._client = None
