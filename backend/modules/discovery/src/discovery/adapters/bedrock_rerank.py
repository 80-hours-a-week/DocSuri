"""BedrockRerankAdapter — real ``RerankAdapter`` via the Amazon Bedrock Rerank API (FR-3).

A cross-encoder that jointly scores (query, document) — priced per-search, off the retrieval
path. Any transport/model error raises ``RerankUnavailable`` so the orchestrator keeps the
baseline RRF order (fail-soft): rerank is a ranking-QUALITY enhancement, never a hard dependency.

Default model = Cohere Rerank on Bedrock (provider-consistent with the Cohere Embed v4 query
embedder). Unit tests exercise the deterministic mock; the real wire shape
(``bedrock-agent-runtime.rerank``) is validated live once the deployment prerequisites below hold.

**Deployment prerequisites (verified 2026-07-06, account 028317349537):**
- The Rerank model is NOT in ap-northeast-2 (Seoul, the deploy region) — only ``cohere.embed-v4``
  is. Point ``model_arn`` + ``region_name`` at a region that HAS it (us-west-2 carries both
  ``cohere.rerank-v3-5`` and ``amazon.rerank-v1``; us-east-1 carries Cohere). This is a
  cross-region call, so budget the extra RTT against NFR-P1.
- The task role needs ``bedrock:Rerank`` on the rerank model resource AND model access enabled in
  that region. Without it the call returns ``AccessDeniedException`` → RerankUnavailable →
  fail-soft to the baseline RRF order (search unaffected). Until these are granted, wiring the
  adapter (setting ``DOCSURI_RERANK_MODEL_ARN``) is a safe no-op: the reranker degrades to baseline.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..ports.search_ports import RerankUnavailable


class BedrockRerankAdapter:
    """Cross-encoder rerank via the Bedrock Rerank API (default: Cohere Rerank v3.5)."""

    def __init__(
        self,
        *,
        model_arn: str,
        region_name: str | None = None,
        client: Any | None = None,
    ) -> None:
        if client is None:
            import boto3  # lazy: only the `real` extra needs boto3
            from botocore.config import Config

            # Bounded — rerank sits on the synchronous search path (NFR-P1 P50<3s). A single
            # attempt: on timeout/error we fail-soft to baseline rather than retry-and-stall.
            config = Config(
                connect_timeout=2.0,
                read_timeout=5.0,
                retries={"max_attempts": 1},
            )
            client = boto3.client(
                "bedrock-agent-runtime", region_name=region_name, config=config
            )
        self._client = client
        self._model_arn = model_arn

    def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        sources = [
            {
                "type": "INLINE",
                "inlineDocumentSource": {"type": "TEXT", "textDocument": {"text": doc}},
            }
            for doc in documents
        ]
        try:
            response = self._client.rerank(
                queries=[{"type": "TEXT", "textQuery": {"text": query}}],
                sources=sources,
                rerankingConfiguration={
                    "type": "BEDROCK_RERANKING_MODEL",
                    "bedrockRerankingConfiguration": {
                        "numberOfResults": len(documents),
                        "modelConfiguration": {"modelArn": self._model_arn},
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001 — any Bedrock/transport error → fail-soft
            raise RerankUnavailable("Bedrock rerank failed") from exc

        # The API returns results sorted by score; map each back to its input position so the
        # scores align 1:1 with ``documents`` (the port contract). Unscored positions stay 0.0.
        scores = [0.0] * len(documents)
        for item in response.get("results", []):
            idx = item.get("index")
            if isinstance(idx, int) and 0 <= idx < len(scores):
                scores[idx] = float(item.get("relevanceScore", 0.0))
        return scores
