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
        return ResearchJobCreateResponse(jobId=job.jobId, state=job.state)

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

    async def add_message(
        self,
        owner_id: str,
        job_id: str,
        dto: ResearchMessageCreateRequest,
        orchestrator: Any = None,
    ) -> ResearchChatMessage:
        self._repo.get_job(owner_id, job_id)
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
            return user_msg
        result = await _run_evidence(orchestrator, owner_id, dto.content)
        content = _format_turn_result(result)
        return self._repo.add_message(
            ResearchChatMessage(
                jobId=job_id,
                ownerId=owner_id,
                role=ChatRole.ASSISTANT,
                content=content,
                attachments=[],
            )
        )

    def list_messages(self, owner_id: str, job_id: str) -> ResearchMessageListResponse:
        return ResearchMessageListResponse(messages=self._repo.list_messages(owner_id, job_id))


async def _run_evidence(orchestrator: Any, owner_id: str, topic: str) -> Any:
    from docsuri_shared._generated.dtos.evidence_schema import EvidenceRequest, EvidenceScope
    from backend.modules.evidence.models import AgentRunContext, EvidenceSession, EvidenceTurn

    request = EvidenceRequest(topic=topic, scope=EvidenceScope.auto, paperIds=[])
    session = EvidenceSession(owner_id=owner_id)
    turn = EvidenceTurn(session_id=session.session_id, request=request)
    ctx = AgentRunContext(
        session=session,
        current_turn=turn,
        owner_id=owner_id,
        request_id='',
        budget_signal={'state': 'ok'},
    )
    return await asyncio.to_thread(orchestrator.run, ctx, request)


def _format_turn_result(result: Any) -> str:
    from backend.modules.evidence.models import TurnSuccessResult, TurnAbstainResult

    if isinstance(result, TurnSuccessResult):
        return json.dumps(result.outcome.model_dump(), ensure_ascii=False)
    if isinstance(result, TurnAbstainResult):
        return f'[abstain] {result.outcome.abstainReason}'
    return '[error] evidence_unavailable'
