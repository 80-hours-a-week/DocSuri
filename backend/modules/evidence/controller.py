from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.accounts.models import Principal

from .models import (
    TurnAbstainResult,
    TurnErrorResult,
    TurnPendingResult,
    TurnSuccessResult,
)
from .repository import EvidenceRepository
from .service import EvidenceChatService, TurnResponse


def _feature_enabled() -> None:
    if os.getenv('EVIDENCE_AGENT_ENABLED', 'true').lower() not in {'1', 'true', 'yes', 'on'}:
        raise HTTPException(status_code=404, detail='not found')


router = APIRouter(
    prefix='/api/evidence',
    tags=['Evidence'],
    dependencies=[Depends(_feature_enabled)],
)


def get_repo() -> EvidenceRepository:
    raise RuntimeError('evidence repository is not wired')


def get_orchestrator() -> Any:
    raise RuntimeError('evidence orchestrator is not wired')


def get_principal(request: Request) -> Principal:
    principal = getattr(request.state, 'principal', None)
    if principal is None:
        raise HTTPException(status_code=401, detail='authentication required')
    return principal


def get_sqs_enqueue(request: Request):
    return getattr(request.app.state, 'evidence_sqs_enqueue', None)


PRINCIPAL_DEP = Depends(get_principal)
REPO_DEP = Depends(get_repo)
ORCHESTRATOR_DEP = Depends(get_orchestrator)
SQS_ENQUEUE_DEP = Depends(get_sqs_enqueue)


# ---------------------------------------------------------------------------
# 요청/응답 스키마
# ---------------------------------------------------------------------------

class TurnCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    topic: str = Field(..., min_length=1, max_length=2000)
    scope: str | None = Field(None, description='auto | explicit | mixed')
    paper_ids: list[str] | None = Field(None, alias='paperIds')
    session_id: str | None = Field(None, alias='sessionId')
    attachments: list[Any] = Field(default_factory=list)


class SourceRefOut(BaseModel):
    paper_id: str = Field(alias='paperId')
    record_ref: str = Field(alias='recordRef')
    anchor: str | None = None
    quote: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class EvidenceItemOut(BaseModel):
    statement: str
    supporting: list[SourceRefOut]
    conflicting: list[SourceRefOut]


class EvidenceCoverageOut(BaseModel):
    paper_count: int = Field(alias='paperCount')
    query_used: str | None = Field(None, alias='queryUsed')

    model_config = ConfigDict(populate_by_name=True)


class TurnResultOut(BaseModel):
    """INV-EV-5: 벡터 점수·청크 ID·LLM 내부 미노출."""
    state: Literal['ok', 'abstain', 'pending', 'error']
    claims: list[EvidenceItemOut] | None = None
    coverage: EvidenceCoverageOut | None = None
    abstain_reason: str | None = Field(None, alias='abstainReason')
    job_id: str | None = Field(None, alias='jobId')
    started_at: datetime | None = Field(None, alias='startedAt')
    error_code: str | None = Field(None, alias='errorCode')

    model_config = ConfigDict(populate_by_name=True)


class TurnOut(BaseModel):
    session_id: str = Field(alias='sessionId')
    turn_id: str = Field(alias='turnId')
    result: TurnResultOut
    created_at: datetime = Field(alias='createdAt')

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@router.post('/turns', response_model=TurnOut)
async def create_turn(
    body: TurnCreateRequest,
    request: Request,
    principal: Principal = PRINCIPAL_DEP,
    repo: EvidenceRepository = REPO_DEP,
    orchestrator: Any = ORCHESTRATOR_DEP,
    sqs_enqueue: Any = SQS_ENQUEUE_DEP,
) -> TurnOut:
    """채팅 턴 실행 — FR-36, FR-37, NFR-P6."""
    from docsuri_shared._generated.dtos.evidence_schema import EvidenceRequest, EvidenceScope

    request_id = request.headers.get('x-request-id', '')
    ev_request = EvidenceRequest(
        topic=body.topic,
        scope=body.scope or EvidenceScope.auto,
        paperIds=body.paper_ids or [],
        attachments=body.attachments or [],
    )

    try:
        turn_resp: TurnResponse = EvidenceChatService(
            repo=repo,
            orchestrator=orchestrator,
            sqs_enqueue=sqs_enqueue,
        ).run_turn(
            owner_id=principal.user_id,
            request=ev_request,
            session_id=body.session_id,
            budget_signal=getattr(request.state, 'budget_signal', {}),
            request_id=request_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='session not found') from exc

    return TurnOut(
        sessionId=turn_resp.session_id,
        turnId=turn_resp.turn_id,
        result=_serialize_result(turn_resp.result),
        createdAt=turn_resp.created_at,
    )


@router.get('/jobs/{job_id}', response_model=TurnOut)
async def get_job(
    job_id: str,
    principal: Principal = PRINCIPAL_DEP,
    repo: EvidenceRepository = REPO_DEP,
) -> TurnOut:
    """비동기 잡 폴링 — BR-EV-6, NFR-P6."""
    try:
        turn = repo.get_turn_by_job_id(principal.user_id, job_id)
    except (KeyError, AttributeError) as exc:
        raise HTTPException(status_code=404, detail='job not found') from exc

    return TurnOut(
        sessionId=turn.session_id,
        turnId=turn.turn_id,
        result=_serialize_result(turn.result),
        createdAt=turn.created_at,
    )


# ---------------------------------------------------------------------------
# 직렬화 헬퍼 — INV-EV-5: 내부 필드 비노출
# ---------------------------------------------------------------------------

def _serialize_result(result: Any) -> TurnResultOut:
    if isinstance(result, TurnSuccessResult):
        outcome = result.outcome
        return TurnResultOut(
            state='ok',
            claims=[
                EvidenceItemOut(
                    statement=item.statement,
                    supporting=[
                        SourceRefOut(
                            paperId=ref.paperId,
                            recordRef=ref.recordRef,
                            anchor=ref.anchor,
                            quote=ref.quote,
                        )
                        for ref in item.supporting
                    ],
                    conflicting=[
                        SourceRefOut(
                            paperId=ref.paperId,
                            recordRef=ref.recordRef,
                            anchor=ref.anchor,
                            quote=ref.quote,
                        )
                        for ref in item.conflicting
                    ],
                )
                for item in outcome.claims
            ],
            coverage=EvidenceCoverageOut(
                paperCount=outcome.coverage.paperCount,
                queryUsed=outcome.coverage.queryUsed,
            ),
        )

    if isinstance(result, TurnAbstainResult):
        return TurnResultOut(
            state='abstain',
            abstainReason=result.outcome.abstainReason,
        )

    if isinstance(result, TurnPendingResult):
        return TurnResultOut(
            state='pending',
            jobId=result.job_id,
            startedAt=result.started_at,
        )

    if isinstance(result, TurnErrorResult):
        return TurnResultOut(
            state='error',
            errorCode=result.error_code,
        )

    return TurnResultOut(state='pending')


routers = (router,)
