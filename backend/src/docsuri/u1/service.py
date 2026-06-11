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
    # mapper·expander는 query 단위 결과를 CachePort에 캐시한다 (동일 입력 중복 LLM 호출 차단).
    mapper = KoEnQueryMapper(u0.llm, u0.cache)
    expander = KeywordExpander(u0.llm, u0.cache)
    estimator = DifficultyEstimator()
    return U1Services(
        orchestrator=SearchOrchestrator(u0, mapper, expander, estimator),
        mapper=mapper,
        expander=expander,
        estimator=estimator,
        filter_sort=FilterSortController(u0.session),
    )
