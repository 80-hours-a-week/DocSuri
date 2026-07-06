"""evidence/tools.py — EvidencePaperSearchTool 예외 변환 회귀 테스트.

배경: real_wiring.py는 OpenSearch 어댑터를 최상위 discovery.* 경로에서 import하는데,
tools.py는 IndexUnavailable을 backend.modules.discovery.src.discovery.* (중첩 경로)에서
import하고 있었다. 소스는 동일해도 Python은 두 경로를 별개 모듈로 취급해 두 IndexUnavailable
클래스가 서로 다른 객체가 되고, tools.py의 `except IndexUnavailable`이 실제로 발생한
예외와 매칭에 실패해 raw 500으로 새어나갔다(프로덕션에서 OpenSearch 콜드 그래프 로드로
재현·확인됨). 이 테스트는 real_wiring.py와 동일한 최상위 경로에서 IndexUnavailable을
raise하는 fake 어댑터로 이 클래스 불일치가 재발하지 않는지 검증한다.
"""

from __future__ import annotations

import pytest
from discovery.ports.search_ports import IndexUnavailable

from backend.modules.evidence.tools import EvidencePaperSearchTool, PaperSearchUnavailable


class _FailingVectorStore:
    def knn_search(self, *args, **kwargs):
        raise IndexUnavailable('search after 3 attempt(s)')


class _FailingLexicalIndex:
    def bm25_search(self, *args, **kwargs):
        raise IndexUnavailable('search after 3 attempt(s)')


class _NoEmbedding:
    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError('embedding backend unavailable')


def _search_tool() -> EvidencePaperSearchTool:
    return EvidencePaperSearchTool(
        embedding=_NoEmbedding(),
        vector_store=_FailingVectorStore(),
        lexical_index=_FailingLexicalIndex(),
        paper_lookup=None,
    )


def test_index_unavailable_from_top_level_discovery_path_is_caught() -> None:
    """real_wiring.py가 실제로 쓰는 최상위 discovery.ports.search_ports.IndexUnavailable을
    그대로 raise해도 PaperSearchUnavailable로 정상 변환돼야 한다(raw로 새면 안 됨)."""
    with pytest.raises(PaperSearchUnavailable):
        _search_tool().search(topic='self-attention', scope=None, paper_ids=None)


def test_index_unavailable_never_escapes_as_itself() -> None:
    """IndexUnavailable 자체가 그대로 호출자까지 전파되면 안 된다 — 반드시
    PaperSearchUnavailable로 변환된 채로만 나가야 orchestrator가 abstain으로 잡을 수 있다."""
    try:
        _search_tool().search(topic='self-attention', scope=None, paper_ids=None)
    except IndexUnavailable:
        pytest.fail('IndexUnavailable leaked raw — tools.py의 except가 매칭에 실패함')
    except PaperSearchUnavailable:
        pass
