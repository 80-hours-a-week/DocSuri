"""U2 조립 — build_u2(u0) 팩토리. U1 build_u1 패턴 미러링 (u2_ui_build_plan A1).

U2 도메인 모듈(타 팀원 작성)은 무수정 재사용 — 여기서는 U0 포트와의
와이어링만 한다. SectionToggleController는 서버 세션 기반이라 본 라운드
(Lambda 무상태)에서는 조립하지 않는다 — COMP-02는 프론트 sessionStorage가 담당.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..u0.adapters import U0Ports
from .document_ingestor import DocumentIngestor
from .summary_engine import SummaryEngine
from .translator import SelectionTranslator


@dataclass(frozen=True)
class U2Services:
    ingestor: DocumentIngestor
    summary_engine: SummaryEngine
    translator: SelectionTranslator


def build_u2(u0: U0Ports) -> U2Services:
    return U2Services(
        ingestor=DocumentIngestor(telemetry=u0.telemetry),
        summary_engine=SummaryEngine(
            llm=u0.llm, cache=u0.cache, glossary=u0.glossary, telemetry=u0.telemetry
        ),
        translator=SelectionTranslator(
            llm=u0.llm, glossary=u0.glossary, telemetry=u0.telemetry
        ),
    )
