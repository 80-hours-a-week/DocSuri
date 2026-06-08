"""Deterministic offline LLM (no API key required).

Used by `container.llm()` when `ANTHROPIC_API_KEY` is not set so the
walking-skeleton demo + the test suite can run with no network.

- purpose="summary"     → 3-sentence stub with `[§abstract]` anchors,
                          stitched from user-prompt fragments.
- purpose="translation" → tiny English→Korean dictionary substitution
                          + `-한다` 체 termination (AGENTS.md §6.3).
- purpose="verify" / "normalize" → trivial echo (Sprint 2 will wire the
                          real Haiku entailment via ClaudeAdapter).

Cache-hit semantics: second identical request returns `cache_hit=True`.
The cache key is derived by `cache_keys.derive_cache_key` (§4.1 single
owner). The instance keeps a tiny in-memory set of seen keys.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

from app.infra.llm.cache_keys import derive_cache_key
from app.infra.llm.protocol import LLMRequest, LLMResponse

# Pre-seeded mini-glossary so the demo shows non-trivial Korean output
# without a network call.
_MOCK_GLOSSARY: dict[str, str] = {
    "transformer": "트랜스포머",
    "attention": "주의",
    "embedding": "임베딩",
    "model": "모델",
    "neural network": "신경망",
    "language model": "언어 모델",
    "self-attention": "자기 주의",
    "encoder": "인코더",
    "decoder": "디코더",
    "token": "토큰",
}


def _ko_terminate(text: str) -> str:
    """학술체 `-한다` 체로 종결. AGENTS.md §6.3."""

    # crude — covers the most common 합니다 → 한다 conversion paths.
    text = re.sub(r"합니다([.?!]?)", r"한다\1", text)
    text = re.sub(r"입니다([.?!]?)", r"이다\1", text)
    text = re.sub(r"됩니다([.?!]?)", r"된다\1", text)
    text = re.sub(r"있습니다([.?!]?)", r"있다\1", text)
    return text


def _translate_span(span: str) -> str:
    """Tiny rule-based English→Korean. Multi-word terms first."""

    out = span
    # longest keys first so "neural network" beats "network"/"model" partials
    for en, ko in sorted(_MOCK_GLOSSARY.items(), key=lambda kv: -len(kv[0])):
        out = re.sub(rf"(?i)\b{re.escape(en)}\b", ko, out)
    # If the LLM "would have said" 합니다, force 한다.
    return _ko_terminate(out)


def _fake_summary(user_message: str) -> str:
    """Build a 3-sentence stub that includes `[§abstract]` anchors.

    Uses fragments from `user_message` so the demo response looks tied
    to the request without any real generation.
    """

    cleaned = re.sub(r"\s+", " ", user_message).strip()
    snippet = cleaned[:120] if cleaned else "본 논문은 입력된 요청을 처리한다"
    return (
        f"본 요약은 데모용 모의 응답이다 [§abstract]. "
        f"요청 발췌: {snippet} [§abstract]. "
        f"실제 Claude 호출 시 동일한 형식으로 응답을 반환한다 [§abstract]."
    )


class MockLLM:
    """Implements `LLMPort` without any external dependency."""

    def __init__(self) -> None:
        # cache_key → previously-returned text. Keeps cache_hit detection
        # deterministic across calls within a process.
        self._cache: dict[str, str] = {}

    async def complete(self, req: LLMRequest) -> LLMResponse:  # noqa: D401
        key = derive_cache_key(req)
        cache_hit = key in self._cache

        if req.purpose == "translation":
            text = _translate_span(req.user_message)
        elif req.purpose == "summary":
            text = _fake_summary(req.user_message)
        elif req.purpose == "verify":
            text = "SUPPORTED"
        else:  # normalize / fallthrough
            text = req.user_message

        # Remember the response so the same request reports cache_hit on retry.
        self._cache.setdefault(key, text)

        # Token counts are made-up but plausible.
        input_tokens = sum(len(b.text) for b in req.system_blocks) // 4 + len(req.user_message) // 4
        output_tokens = len(text) // 4

        return LLMResponse(
            text=text,
            cache_hit=cache_hit,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model="mock-deterministic",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[str]:
        """Emit the deterministic stub as NDJSON lines, one chunk at a time.

        The summary path expects line-per-sentence so the SSE endpoint can
        forward each completed sentence to the FE the moment it arrives.
        We synthesise that shape from `_fake_summary` so mock-mode visibly
        streams in the demo too.
        """
        if req.purpose == "summary":
            sentences = [
                "본 요약은 데모용 모의 응답이다 [§abstract].",
                "실제 Claude 호출 시 동일한 형식으로 응답을 반환한다 [§abstract].",
                "스트리밍 SSE 경로로 sentence가 순차적으로 도착한다 [§abstract].",
            ]
            for s in sentences:
                line = json.dumps(
                    {"type": "sentence", "text": s, "anchor": "[§abstract]"},
                    ensure_ascii=False,
                ) + "\n"
                # Yield in 2 chunks per line to prove incremental assembly.
                mid = len(line) // 2
                yield line[:mid]
                await asyncio.sleep(0.25)
                yield line[mid:]
                await asyncio.sleep(0.1)
            tail = json.dumps(
                {"type": "done", "glossary_additions": []}, ensure_ascii=False
            ) + "\n"
            yield tail
            return

        # Non-summary purposes degrade gracefully to a single delta.
        resp = await self.complete(req)
        yield resp.text
