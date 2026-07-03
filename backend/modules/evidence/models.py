from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from docsuri_shared._generated.dtos.evidence_schema import (
    EvidenceAbstainResult,
    EvidenceRequest,
    EvidenceResult,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


class SessionStatus(StrEnum):
    ACTIVE = 'active'
    DELETED = 'deleted'


# TurnResult 변형

@dataclass(frozen=True)
class TurnSuccessResult:
    outcome: EvidenceResult


@dataclass(frozen=True)
class TurnAbstainResult:
    outcome: EvidenceAbstainResult


@dataclass(frozen=True)
class TurnPendingResult:
    job_id: str
    started_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class TurnErrorResult:
    # 내부 상세 비노출(SEC-9) — errorCode만 반환
    error_code: str


TurnResult = TurnSuccessResult | TurnAbstainResult | TurnPendingResult | TurnErrorResult


@dataclass
class EvidenceTurn:
    turn_id: str = field(default_factory=_new_id)
    session_id: str = ''
    request: EvidenceRequest | None = None
    result: TurnResult | None = None
    created_at: datetime = field(default_factory=_utc_now)
    # 비동기 잡 폴링용 식별자(BR-EV-6) — TurnPendingResult.job_id에서 생성 시 한 번만
    # 복사해온다. result가 terminal로 교체된 뒤에도 get_turn_by_job_id가 계속 조회할 수
    # 있어야 하는데, job_id가 result 안에만 있으면 완료 즉시 사라져 404가 났었다
    # (PR #338 리뷰 Blocking #2).
    job_id: str | None = None


@dataclass
class EvidenceSession:
    session_id: str = field(default_factory=_new_id)
    owner_id: str = ''
    title: str | None = None
    turns: list[EvidenceTurn] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class AgentRunContext:
    session: EvidenceSession
    current_turn: EvidenceTurn
    owner_id: str
    request_id: str
    budget_signal: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaperSearchResult:
    records: tuple[Any, ...]  # IndexRecord[]
    query_used: str | None
    scope: str  # EvidenceScope value


@dataclass(frozen=True)
class AttachmentHandle:
    attachment_id: str
    mime_type: str
    size_bytes: int
