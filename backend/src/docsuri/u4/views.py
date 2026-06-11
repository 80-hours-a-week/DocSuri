"""U4 Trace 출력 DTO — component-model §6.6 시그니처 그대로 (동결).

`CitationView`는 U4의 "유일한 약속" — 데스크톱 그래프 / 모바일·학부 리스트가
같은 구조를 소비한다 (TRACE-01·02).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..u0.ports import PaperHit

RenderMode = Literal["graph", "list"]

MAX_NODES = 30  # TRACE-01 AC: "그래프는 최대 30개 노드로 제한"


class CitationView(BaseModel):
    center: PaperHit
    outgoing: list[PaperHit]
    incoming: list[PaperHit]
    render: RenderMode
    max_nodes: int = MAX_NODES
