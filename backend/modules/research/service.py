from __future__ import annotations

import asyncio
import json
from typing import Any

from .models import (
    ChatRole,
    ResearchChatMessage,
    ResearchJob,
    ResearchJobCreateRequest,
    ResearchJobCreateResponse,
    ResearchJobDetailResponse,
    ResearchJobListResponse,
    ResearchJobState,
    ResearchJobSummary,
    ResearchMessageCreateRequest,
    ResearchMessageListResponse,
    title_from_content,
)
from .repository import ResearchRepository


class ResearchService:
    def __init__(self, repo: ResearchRepository) -> None:
        self._repo = repo

    async def create_job(
        self,
        owner_id: str,
        dto: ResearchJobCreateRequest,
        orchestrator: Any = None,
    ) -> ResearchJobCreateResponse:
        job = self._repo.create_job(
            ResearchJob(ownerId=owner_id, title=title_from_content(dto.content))
        )
        await self.add_message(owner_id, job.jobId, dto, orchestrator)
        # add_message가 처리 완료 후 항상 COMPLETED로 전이시키므로(PR #338 Blocking #3)
        # 응답도 그 최종 상태를 반영해야 한다 — job은 create_job 호출 시점의 스냅샷이라
        # 그대로 두면 항상 ACTIVE로 보고된다.
        return ResearchJobCreateResponse(jobId=job.jobId, state=ResearchJobState.COMPLETED)

    def list_jobs(self, owner_id: str, limit: int = 50) -> ResearchJobListResponse:
        jobs = self._repo.list_jobs(owner_id, max(1, min(limit, 100)))
        return ResearchJobListResponse(
            jobs=[
                ResearchJobSummary(
                    jobId=job.jobId,
                    title=job.title,
                    state=job.state,
                    createdAt=job.createdAt,
                    updatedAt=job.updatedAt,
                )
                for job in jobs
            ]
        )

    def detail(self, owner_id: str, job_id: str) -> ResearchJobDetailResponse:
        return ResearchJobDetailResponse(
            job=self._repo.get_job(owner_id, job_id),
            messages=self._repo.list_messages(owner_id, job_id),
        )

    def delete_job(self, owner_id: str, job_id: str) -> None:
        self._repo.delete_job(owner_id, job_id)

    def delete_all_jobs(self, owner_id: str) -> None:
        self._repo.delete_all_jobs(owner_id)

    async def add_message(
        self,
        owner_id: str,
        job_id: str,
        dto: ResearchMessageCreateRequest,
        orchestrator: Any = None,
    ) -> ResearchChatMessage:
        self._repo.get_job(owner_id, job_id)
        # 멀티턴 맥락(PR #338 리뷰 Blocking #2/FR-37): 현재 메시지 추가 전 이전 사용자 질문들.
        prior_topics = tuple(
            m.content
            for m in self._repo.list_messages(owner_id, job_id)
            if m.role == ChatRole.USER and m.content
        )
        user_msg = self._repo.add_message(
            ResearchChatMessage(
                jobId=job_id,
                ownerId=owner_id,
                role=ChatRole.USER,
                content=dto.content,
                attachments=dto.attachments,
            )
        )
        if orchestrator is None:
            self._repo.mark_completed(owner_id, job_id)
            return user_msg
        result = await _run_evidence(orchestrator, owner_id, dto.content, prior_topics)
        content = _format_turn_result(result)
        assistant_msg = self._repo.add_message(
            ResearchChatMessage(
                jobId=job_id,
                ownerId=owner_id,
                role=ChatRole.ASSISTANT,
                content=content,
                attachments=[],
            )
        )
        # 이 요청이 반환되는 시점에는 이미 모든 처리(evidence 추출 포함)가 끝난
        # 상태다 — job.state를 ACTIVE로 남겨두면 FE가 running으로 매핑해 답변이
        # 저장된 뒤에도 폴링을 멈추지 않는다(PR #338 리뷰 Blocking #3).
        self._repo.mark_completed(owner_id, job_id)
        return assistant_msg

    def list_messages(self, owner_id: str, job_id: str) -> ResearchMessageListResponse:
        return ResearchMessageListResponse(messages=self._repo.list_messages(owner_id, job_id))


async def _run_evidence(
    orchestrator: Any, owner_id: str, topic: str, prior_topics: tuple[str, ...] = ()
) -> Any:
    from docsuri_shared._generated.dtos.evidence_schema import EvidenceRequest, EvidenceScope
    from pydantic import ValidationError

    from backend.modules.evidence.models import AgentRunContext, EvidenceSession, EvidenceTurn

    try:
        # research content 한도(12000) > evidence topic 한도(2000)라, 긴 메시지가 여기서
        # EvidenceRequest Pydantic 검증에 걸려 HTTP 500이 나던 걸 degrade로 막는다
        # (PR #338 리뷰 Blocking #3/SEC-5). controller 경로는 경계(2000)에서 422로 처리.
        request = EvidenceRequest(topic=topic, scope=EvidenceScope.auto, paperIds=[])
    except ValidationError:
        return None
    session = EvidenceSession(owner_id=owner_id)
    turn = EvidenceTurn(session_id=session.session_id, request=request)
    ctx = AgentRunContext(
        session=session,
        current_turn=turn,
        owner_id=owner_id,
        request_id='',
        budget_signal={'state': 'ok'},
        prior_topics=prior_topics,
    )
    return await asyncio.to_thread(orchestrator.run, ctx, request)


def _format_turn_result(result: Any) -> str:
    from backend.modules.evidence.models import TurnAbstainResult, TurnSuccessResult

    if isinstance(result, TurnSuccessResult):
        return json.dumps(result.outcome.model_dump(), ensure_ascii=False)
    if isinstance(result, TurnAbstainResult):
        return f'[abstain] {result.outcome.abstainReason}'
    return '[error] evidence_unavailable'
