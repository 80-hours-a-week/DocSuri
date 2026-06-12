"""U2 HTTP 표면 — FastAPI APIRouter (u1/api.py 패턴, u2_ui_build_plan A2).

POST /api/summaries     { paper_id | arxiv_url, mode } → { summary: SummaryResult(동결 §3),
                          readability: ReadabilityReport | null }  — 엔벨로프는 U1 전례
POST /api/translations  { source_excerpt, input_mode } → TranslationResult

둘 다 실 LLM 과금 엔드포인트 — 입력 형식·길이를 엄격히 검증한다 (u1 safety 원칙).
본문 소스는 arXiv 초록(DocumentIngestor) — MVP 데모 범위 (계획 '설계 결정').
"""

from __future__ import annotations

import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from ..u0.http_policy import NetworkRetryExceeded
from ..u0.ports import Persona
from .models import (
    DocumentSource,
    InputMode,
    ReadabilityReport,
    SummaryResult,
    TranslationResult,
    TranslationSelection,
)
from .service import U2Services

ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_URL_RE = re.compile(r"^https?://arxiv\.org/(abs|pdf)/\d{4}\.\d{4,5}(v\d+)?/?$")
MAX_EXCERPT_LEN = 2_000  # 번역 입력 상한 — 토큰 비용 방어


class SummaryRequest(BaseModel):
    paper_id: str | None = None
    arxiv_url: str | None = None
    mode: Persona = "pro"

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "SummaryRequest":
        if self.paper_id is not None and not ARXIV_ID_RE.match(self.paper_id):
            raise ValueError("paper_id는 arXiv ID 형식(예: 2606.13443)이어야 합니다.")
        if self.arxiv_url is not None and not ARXIV_URL_RE.match(self.arxiv_url):
            raise ValueError("arxiv_url은 arxiv.org abs/pdf 주소만 허용합니다.")
        if (self.paper_id is None) == (self.arxiv_url is None):
            raise ValueError("paper_id 또는 arxiv_url 중 정확히 하나를 보내야 합니다.")
        return self

    def to_source(self) -> DocumentSource:
        url = self.arxiv_url or f"https://arxiv.org/abs/{self.paper_id}"
        return DocumentSource(kind="arxiv_url", value=url, paper_id=self.paper_id)


class SourcePaper(BaseModel):
    """UI 보조 — COMP-04 번역 패널이 표시할 영문 원문(초록)."""

    title: str
    abstract: str


class SummaryResponse(BaseModel):
    summary: SummaryResult
    readability: ReadabilityReport | None = None  # UI 보조 — 학부 모드 가독성 표시
    paper: SourcePaper


class TranslationRequest(BaseModel):
    source_excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LEN)
    input_mode: InputMode = "desktop"

    @model_validator(mode="after")
    def _not_blank(self) -> "TranslationRequest":
        cleaned = " ".join(
            ch for ch in self.source_excerpt if ch.isprintable() or ch.isspace()
        ).strip()
        if not cleaned:
            raise ValueError("번역할 텍스트가 비어 있습니다.")
        return self


def build_router(services: U2Services) -> APIRouter:
    router = APIRouter()

    @router.post("/api/summaries", response_model=SummaryResponse)
    def summarize(req: SummaryRequest) -> SummaryResponse:
        try:
            paper_text = services.ingestor.ingest(req.to_source())
        except (NetworkRetryExceeded, httpx.HTTPError) as exc:
            raise HTTPException(
                status_code=502, detail="arXiv에서 원문을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=f"원문을 가져오지 못했습니다: {exc}") from exc
        summary = services.summary_engine.summarize(paper_text, req.mode)
        return SummaryResponse(
            summary=summary,
            readability=services.summary_engine.last_readability_report,
            paper=SourcePaper(
                title=paper_text.title,
                abstract=paper_text.sections[0].text if paper_text.sections else "",
            ),
        )

    @router.post("/api/translations", response_model=TranslationResult)
    def translate(req: TranslationRequest) -> TranslationResult:
        selection = TranslationSelection(
            source_excerpt=req.source_excerpt.strip(), input_mode=req.input_mode
        )
        return services.translator.translate(selection)

    return router
