"""AWS Bedrock Claude adapter implementing `LLMPort`.

Uses boto3 `bedrock-runtime` Converse API — structurally identical to the
Anthropic messages API but routed through AWS. boto3 is synchronous so
`complete()` and the stream collector both run via `asyncio.to_thread`.

Model routing by `LLMRequest.purpose`:
- summary / translation → Sonnet (configurable via BEDROCK_SONNET_MODEL)
- verify / normalize    → Haiku  (configurable via BEDROCK_HAIKU_MODEL)

Required env: AWS_BEDROCK_REGION (e.g. us-east-1).
AWS credentials are resolved by boto3 in the standard order:
  env vars → ~/.aws/credentials → IAM instance role.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from app.infra.llm.protocol import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

_DEFAULT_HAIKU = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
_DEFAULT_SONNET = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def _pick_model(purpose: str) -> str:
    if purpose in ("verify", "normalize"):
        return os.getenv("BEDROCK_HAIKU_MODEL", _DEFAULT_HAIKU)
    return os.getenv("BEDROCK_SONNET_MODEL", _DEFAULT_SONNET)


class BedrockAdapter:
    """AWS Bedrock Claude adapter.

    Wired by `container.llm()` when `AWS_BEDROCK_REGION` is set.
    Falls back to `MockLLM` when neither Bedrock nor Anthropic is configured.
    """

    def __init__(self, region: str | None = None) -> None:
        self._region = region or os.getenv("AWS_BEDROCK_REGION", "us-east-1")
        self._client = None  # lazy

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "boto3 not installed; run `pip install boto3` or "
                "unset AWS_BEDROCK_REGION to use MockLLM."
            ) from exc
        self._client = boto3.client("bedrock-runtime", region_name=self._region)
        return self._client

    async def complete(self, req: LLMRequest) -> LLMResponse:
        model = _pick_model(req.purpose)

        system = [{"text": block.text} for block in req.system_blocks]
        messages = [{"role": "user", "content": [{"text": req.user_message}]}]
        inference_cfg = {"maxTokens": req.max_tokens, "temperature": req.temperature}

        def _call() -> dict:
            client = self._ensure_client()
            return client.converse(  # type: ignore[attr-defined]
                modelId=model,
                system=system,
                messages=messages,
                inferenceConfig=inference_cfg,
            )

        resp = await asyncio.to_thread(_call)

        text = resp["output"]["message"]["content"][0]["text"]
        usage = resp.get("usage", {})
        cache_read = usage.get("cacheReadInputTokens", 0) or 0

        logger.info(
            "bedrock.complete model=%s in=%d out=%d cache_hit=%s",
            model,
            usage.get("inputTokens", 0),
            usage.get("outputTokens", 0),
            cache_read > 0,
        )

        return LLMResponse(
            text=text,
            cache_hit=cache_read > 0,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            model=model,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[str]:
        """Yield text deltas from Bedrock converse_stream.

        boto3 stream iteration is synchronous; chunks are collected in a
        thread then yielded to keep the async interface consistent.
        """
        model = _pick_model(req.purpose)

        system = [{"text": block.text} for block in req.system_blocks]
        messages = [{"role": "user", "content": [{"text": req.user_message}]}]
        inference_cfg = {"maxTokens": req.max_tokens, "temperature": req.temperature}

        def _collect() -> list[str]:
            client = self._ensure_client()
            resp = client.converse_stream(  # type: ignore[attr-defined]
                modelId=model,
                system=system,
                messages=messages,
                inferenceConfig=inference_cfg,
            )
            chunks: list[str] = []
            for event in resp.get("stream", []):
                delta = event.get("contentBlockDelta", {}).get("delta", {})
                text = delta.get("text", "")
                if text:
                    chunks.append(text)
            return chunks

        for chunk in await asyncio.to_thread(_collect):
            yield chunk
