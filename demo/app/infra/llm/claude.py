"""Anthropic Claude adapter implementing `LLMPort` (AGENTS.md §4.1).

Per AGENTS.md §4.1, `infra/llm` is the sole owner of `cache_control:
ephemeral` semantics and prompt-cache key derivation. Domain modules
never see either.

Model routing by `LLMRequest.purpose`:
- summary / translation → Sonnet 4.6
- verify / normalize    → Haiku 4.5

The `anthropic` SDK is imported lazily inside `complete()` so a missing
package does not break startup (the demo defaults to `MockLLM`).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from app.infra.llm.cache_keys import derive_cache_key
from app.infra.llm.protocol import LLMRequest, LLMResponse

if TYPE_CHECKING:  # pragma: no cover — type-checking only
    pass

SONNET_MODEL = "claude-sonnet-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"


def _pick_model(purpose: str) -> str:
    if purpose in ("verify", "normalize"):
        return HAIKU_MODEL
    return SONNET_MODEL


class ClaudeAdapter:
    """Real Anthropic Claude adapter.

    NOTE: This adapter is wired by `container.llm()` only when
    `ANTHROPIC_API_KEY` is set. The walking-skeleton demo's tests rely
    on `MockLLM` so this code is exercised at runtime only.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None  # lazy

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover — runtime-only path
            raise RuntimeError(
                "anthropic SDK not installed; install `anthropic>=0.40` "
                "or unset ANTHROPIC_API_KEY to use MockLLM."
            ) from exc
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(self, req: LLMRequest) -> LLMResponse:
        # Derive the cache key purely for telemetry/audit — Anthropic infers
        # cache hits from the `cache_control` markers on the blocks themselves.
        _ = derive_cache_key(req)

        client = self._ensure_client()
        model = _pick_model(req.purpose)

        # Build a `system` array where every cached block carries
        # `cache_control: ephemeral` (AGENTS.md §4.1, 5min TTL).
        system_param = [
            {
                "type": "text",
                "text": block.text,
                "cache_control": {"type": "ephemeral"},
            }
            for block in req.system_blocks
        ]

        # Lazy import keeps startup clean if anthropic is missing.
        resp = await client.messages.create(  # type: ignore[attr-defined]
            model=model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            system=system_param,
            messages=[{"role": "user", "content": req.user_message}],
        )

        # Aggregate text from the response content blocks.
        text_parts: list[str] = []
        for block in resp.content:  # type: ignore[attr-defined]
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(getattr(block, "text", ""))
        text = "".join(text_parts)

        usage = getattr(resp, "usage", None)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0) if usage else 0
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0

        return LLMResponse(
            text=text,
            cache_hit=cache_read > 0,
            input_tokens=input_tokens + cache_read,
            output_tokens=output_tokens,
            model=model,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[str]:
        """Yield text deltas using Anthropic's native streaming API.

        We forward only `text_delta` events; control frames (message_start,
        content_block_start, etc.) stay inside the SDK. Cache-control
        markers and model routing reuse the same `complete()` logic.
        """

        _ = derive_cache_key(req)  # telemetry parity with complete()

        client = self._ensure_client()
        model = _pick_model(req.purpose)

        system_param = [
            {
                "type": "text",
                "text": block.text,
                "cache_control": {"type": "ephemeral"},
            }
            for block in req.system_blocks
        ]

        # `messages.stream` returns an async context manager. We iterate its
        # text_stream which already coalesces deltas into readable strings.
        async with client.messages.stream(  # type: ignore[attr-defined]
            model=model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            system=system_param,
            messages=[{"role": "user", "content": req.user_message}],
        ) as stream:
            async for delta in stream.text_stream:
                if delta:
                    yield delta
