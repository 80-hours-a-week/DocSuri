"""CostGuard — NFR-COST-01 월 상한 하드 거부 (사용자 결정 2026-06-11).

component-model §2.2: LlmPort 게이트웨이에 내장되어 모든 호출 전후를 감싼다.
무엇을 호출할지는 도메인 unit이 결정하고, 여기서는 예산만 강제한다 (U0 §8).
"""

from __future__ import annotations

import time
from typing import Callable, Protocol


class CostLimitExceeded(Exception):
    """상한 도달 — 하드 거부. 메시지는 사용자 노출용 한국어."""


class CostStore(Protocol):
    def add(self, month_key: str, usd: float, cap: float | None = None) -> float:
        """월 누적에 더하고 누적치를 반환.

        cap이 주어지면 *원자적으로* 강제한다(u0-code-review U0-M1): 기존 누적이
        이미 cap 이상이면 더하지 않고 CostLimitExceeded — check→record 사이의
        동시 호출 경쟁으로 상한을 무한히 넘는 경로를 차단한다(초과는 진행 중
        호출 1건分으로 한정).
        """
        ...

    def total(self, month_key: str) -> float: ...


class InMemoryCostStore:
    def __init__(self) -> None:
        self._totals: dict[str, float] = {}

    def add(self, month_key: str, usd: float, cap: float | None = None) -> float:
        current = self._totals.get(month_key, 0.0)
        if cap is not None and current >= cap:
            raise CostLimitExceeded(
                f"이번 달 LLM 비용 상한(USD {cap:.0f})에 도달하여 요청을 처리할 수 "
                f"없습니다. 다음 달에 다시 시도하거나 운영자에게 문의해 주세요."
            )
        self._totals[month_key] = current + usd
        return self._totals[month_key]

    def total(self, month_key: str) -> float:
        return self._totals.get(month_key, 0.0)


class CostGuard:
    def __init__(
        self,
        store: CostStore,
        monthly_cap_usd: float,
        price_in_per_mtok: float,
        price_out_per_mtok: float,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._store = store
        self._cap = monthly_cap_usd
        self._price_in = price_in_per_mtok
        self._price_out = price_out_per_mtok
        self._clock = clock

    def _month_key(self) -> str:
        return time.strftime("%Y-%m", time.gmtime(self._clock()))

    def _cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in * self._price_in + tokens_out * self._price_out) / 1_000_000

    def check_budget(self, estimated_tokens_in: int, estimated_tokens_out: int) -> None:
        projected = self._store.total(self._month_key()) + self._cost_usd(
            estimated_tokens_in, estimated_tokens_out
        )
        if projected > self._cap:
            raise CostLimitExceeded(
                f"이번 달 LLM 비용 상한(USD {self._cap:.0f})에 도달하여 요청을 처리할 수 "
                f"없습니다. 다음 달에 다시 시도하거나 운영자에게 문의해 주세요."
            )

    def record_cost(self, tokens_in: int, tokens_out: int) -> float:
        # cap을 스토어에 전달해 누적 시점에 원자 강제 (U0-M1) — check_budget은
        # 호출 전 사전 차단(예산 추정), 여기는 실측 기록 시 최종 방어선.
        return self._store.add(
            self._month_key(), self._cost_usd(tokens_in, tokens_out), cap=self._cap
        )

    def accumulated_usd(self) -> float:
        return self._store.total(self._month_key())
