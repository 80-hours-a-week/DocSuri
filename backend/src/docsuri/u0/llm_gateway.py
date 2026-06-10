"""LlmPort 게이트웨이 — component-model §2.2: CostGuard가 모든 호출 전후를 감싸고
Telemetry가 자동 기록된다. 도메인 unit은 이 게이트웨이만 본다."""

from __future__ import annotations

import time

from .cost_guard import CostGuard
from .ports import Completion, LlmPort, Persona, Telemetry, TelemetryEvent


class LlmGateway:
    def __init__(self, inner: LlmPort, guard: CostGuard, telemetry: Telemetry) -> None:
        self._inner = inner
        self._guard = guard
        self._telemetry = telemetry

    def complete(self, prompt: str, persona: Persona, budget_tokens: int) -> Completion:
        # 입력 추정은 보수적으로(프롬프트 길이 기반), 출력 추정은 예산 전체로 잡는다.
        self._guard.check_budget(
            estimated_tokens_in=max(1, len(prompt) // 3),
            estimated_tokens_out=budget_tokens,
        )
        started = time.perf_counter()
        completion = self._inner.complete(prompt, persona, budget_tokens)
        latency_ms = (time.perf_counter() - started) * 1000
        self._guard.record_cost(completion.tokens_in, completion.tokens_out)
        self._telemetry.record(
            TelemetryEvent(
                op="llm.complete",
                latency_ms=round(latency_ms, 3),
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                cache_hit=False,
                persona=persona,
            )
        )
        return completion
