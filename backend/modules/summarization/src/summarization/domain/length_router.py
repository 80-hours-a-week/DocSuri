"""LengthRouter — single-call vs map-reduce branch (BR-S6 / Q3).

Shape only: the concrete token budget / chunk size / async-job switchover are runtime
tunes (NFR/Code-gen). The default budget keeps the common paper (~13K, up to ~40K tokens)
on the single-call path; map-reduce is the bounded outlier path (v1 stays synchronous,
TD-S9). An input token cap bounds extreme outliers.
"""

from __future__ import annotations

from enum import StrEnum

# Conservative defaults (tunable). Single call for the vast majority; cap bounds outliers.
DEFAULT_CONTEXT_BUDGET_TOKENS = 40_000
DEFAULT_INPUT_CAP_TOKENS = 120_000


class LengthRoute(StrEnum):
    SINGLE = "single"
    MAP_REDUCE = "map_reduce"
    OVER_CAP = "over_cap"  # beyond the input cap → explicit degrade/abstain


class LengthRouter:
    def __init__(
        self,
        *,
        context_budget: int = DEFAULT_CONTEXT_BUDGET_TOKENS,
        input_cap: int = DEFAULT_INPUT_CAP_TOKENS,
    ) -> None:
        self._budget = context_budget
        self._cap = input_cap

    def route(self, token_count: int) -> LengthRoute:
        if token_count > self._cap:
            return LengthRoute.OVER_CAP
        if token_count > self._budget:
            return LengthRoute.MAP_REDUCE
        return LengthRoute.SINGLE
