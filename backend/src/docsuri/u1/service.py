"""U1 조립 — build_u1(u0) 팩토리. U0의 build_u0 패턴 미러링.

U0Ports(주입된 포트 묶음)를 받아 U1 도메인 컴포넌트를 와이어링한다.
도메인 컴포넌트는 mock/aws 모드와 무관 — U0 포트 뒤에서 구현이 교체된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..u0.adapters import U0Ports
from .difficulty import DifficultyEstimator
from .filter_sort import FilterSortController
from .keyword_expander import KeywordExpander
from .orchestrator import SearchOrchestrator
from .query_mapper import KoEnQueryMapper


@dataclass(frozen=True)
class U1Services:
    orchestrator: SearchOrchestrator
    mapper: KoEnQueryMapper
    expander: KeywordExpander
    estimator: DifficultyEstimator
    filter_sort: FilterSortController


def build_u1(u0: U0Ports) -> U1Services:
    mapper = KoEnQueryMapper(u0.llm)
    expander = KeywordExpander(u0.llm)
    estimator = DifficultyEstimator()
    return U1Services(
        orchestrator=SearchOrchestrator(u0, mapper, expander, estimator),
        mapper=mapper,
        expander=expander,
        estimator=estimator,
        filter_sort=FilterSortController(u0.session),
    )
