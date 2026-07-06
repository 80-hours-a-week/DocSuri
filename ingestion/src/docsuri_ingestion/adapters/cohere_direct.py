"""CohereDirectEmbeddingPort — embed via Cohere's own API, NOT Bedrock.

Same model + embedding space as ``BedrockCohereEmbeddingPort`` (Cohere Embed v4,
``input_type=search_document``, pinned ``output_dimension``) but calls ``api.cohere.com`` directly.
This bypasses Bedrock's global inference-profile **432M-tokens/day** cap (embed-v4 is
INFERENCE_PROFILE-only on Bedrock: no provisioned throughput, no batch, no regional on-demand),
so a one-off full-corpus re-embed finishes in hours instead of ~3 days.

Interface-compatible with ``BedrockCohereEmbeddingPort`` (same ``embed_documents`` signature) so
``reembed()`` swaps it in behind ``DOCSURI_REEMBED_EMBEDDING_BACKEND=cohere``. Transient failures
(429 / 5xx / transport) raise ``RetriableIngestionError`` so the existing ``_embed_with_retry``
backoff handles them; other 4xx (bad key / bad request) fail fast as permanent config errors.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx
from docsuri_shared.vector_spec import EMBEDDING_SPEC

from ..domain.enums import FailureReason
from ..domain.errors import RetriableIngestionError, ValidationViolationError

# Cohere v2 embed endpoint. A single request caps at 96 texts (same as Cohere-on-Bedrock).
_COHERE_EMBED_URL = "https://api.cohere.com/v2/embed"
_COHERE_EMBED_BATCH_LIMIT = 96
_COHERE_DEFAULT_MODEL = "embed-v4.0"
# 429 (rate limit) + 5xx (transient) → back off & retry via _embed_with_retry. Other 4xx (bad key /
# bad request / model access) are permanent config errors and must fail fast, not retry-storm.
_RETRIABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class CohereDirectEmbeddingPort:
    """Document embedding via Cohere's REST API (Embed v4, writer=search_document)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        output_dimension: int | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Cohere API key is required for CohereDirectEmbeddingPort")
        self._api_key = api_key
        self._model = model or _COHERE_DEFAULT_MODEL
        # Defaults to the frozen spec width (1024). A re-embed to a different space (e.g. Cohere
        # v4's 1536 default) overrides it so the request pin + length check match the new vectors.
        self._output_dimension = output_dimension or EMBEDDING_SPEC.dimensions
        self._client = client or httpx.Client(timeout=timeout)

    def embed_documents(
        self,
        texts: list[str] | tuple[str, ...],
        *,
        correlation_id: str | None = None,
    ) -> list[list[float]]:
        del correlation_id
        if EMBEDDING_SPEC.input_type_writer != "search_document":
            raise RuntimeError("writer must use search_document input type")
        # A long paper can chunk past the 96-text request cap (max_chunks_per_paper=128). Sub-batch
        # and concatenate IN ORDER — the caller zips chunk_ids↔vectors with strict=True.
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _COHERE_EMBED_BATCH_LIMIT):
            vectors.extend(self._embed_batch(texts[start : start + _COHERE_EMBED_BATCH_LIMIT]))
        return vectors

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        body = {
            "model": self._model,
            "texts": list(texts),
            "input_type": EMBEDDING_SPEC.input_type_writer,  # search_document
            "embedding_types": ["float"],
            # Cohere Embed v4 defaults to 1536-dim; pin to the configured width so vectors match
            # the target index mapping (the re-embed override, e.g. 1536).
            "output_dimension": self._output_dimension,
        }
        try:
            response = self._client.post(
                _COHERE_EMBED_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
            )
        except httpx.HTTPError as exc:  # connect/read timeout, transport error → transient
            raise RetriableIngestionError(
                "Cohere embed request failed (transport)",
                reason=FailureReason.DEPENDENCY_UNAVAILABLE,
                stage="embed",
            ) from exc
        if response.status_code in _RETRIABLE_STATUS:
            raise RetriableIngestionError(
                f"Cohere embed transient status {response.status_code}",
                reason=FailureReason.DEPENDENCY_UNAVAILABLE,
                stage="embed",
            )
        if response.status_code >= 400:
            raise ValidationViolationError(
                f"Cohere embed failed {response.status_code}: {response.text[:200]}",
                stage="embed",
            )
        payload = response.json()
        vectors = payload.get("embeddings", {})
        # v2 returns {"embeddings": {"float": [[...]]}}; be tolerant of a bare list too.
        if isinstance(vectors, dict):
            vectors = vectors.get("float", [])
        if not vectors:
            raise ValidationViolationError("Cohere returned no embeddings", stage="embed")
        for vector in vectors:
            if len(vector) != self._output_dimension:
                raise ValidationViolationError(
                    f"Cohere returned vector dimension {len(vector)}, "
                    f"expected {self._output_dimension}",
                    stage="embed",
                )
        return vectors
