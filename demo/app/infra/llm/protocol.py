"""Owner port for LLM access (AGENTS.md §4.1).

`infra/llm/` is the SOLE owner of prompt-cache keys. Domain modules call
this Protocol; they never know whether the implementation is Claude,
the deterministic mock, or a future provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class CachedBlock:
    """A `cache_control: ephemeral` block (AGENTS.md §4.1, 5min TTL)."""

    text: str
    name: str  # used in cache-key derivation; infra owns the key namespace


@dataclass
class LLMRequest:
    system_blocks: list[CachedBlock]
    user_message: str
    max_tokens: int = 1024
    temperature: float = 0.2
    purpose: Literal["summary", "translation", "verify", "normalize"] = "summary"


@dataclass
class LLMResponse:
    text: str
    cache_hit: bool
    input_tokens: int
    output_tokens: int
    model: str


class LLMPort(Protocol):
    """Domain calls only this."""

    async def complete(self, req: LLMRequest) -> LLMResponse:
        ...

    def stream(self, req: LLMRequest) -> AsyncIterator[str]:
        """Yield text deltas as the model produces them.

        Implementations should yield small strings (tokens or words) and
        complete when the model stops. Cache-hit semantics are not part of
        the streaming contract — they live on the non-streaming `complete`
        path. The domain layer uses `stream` for progressive UX and
        `complete` for one-shot calls (e.g. verify).
        """
        ...
