"""NFR-C1 — 에이전트 경로(evidence turn / novelty job) 사용자별 일일 쿼터."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.middleware import agent_quota
from backend.middleware.rate_limit import InProcessWindowLimiter


def _request(user_id: str | None = "u1") -> SimpleNamespace:
    principal = SimpleNamespace(user_id=user_id) if user_id else None
    return SimpleNamespace(state=SimpleNamespace(principal=principal))


@pytest.fixture()
def limiter(monkeypatch: pytest.MonkeyPatch) -> InProcessWindowLimiter:
    shared = InProcessWindowLimiter()
    monkeypatch.setattr(agent_quota, "get_shared_limiter", lambda: shared)
    return shared


def test_evidence_turn_quota_blocks_after_daily_limit(limiter, monkeypatch) -> None:
    monkeypatch.setattr(agent_quota, "_EVIDENCE_DAILY_LIMIT", 2)

    asyncio.run(agent_quota.enforce_evidence_turn_quota(_request()))
    asyncio.run(agent_quota.enforce_evidence_turn_quota(_request()))
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(agent_quota.enforce_evidence_turn_quota(_request()))

    assert excinfo.value.status_code == 429


def test_quota_is_isolated_per_user_and_per_scope(limiter, monkeypatch) -> None:
    monkeypatch.setattr(agent_quota, "_EVIDENCE_DAILY_LIMIT", 1)
    monkeypatch.setattr(agent_quota, "_NOVELTY_DAILY_LIMIT", 1)

    asyncio.run(agent_quota.enforce_evidence_turn_quota(_request("a")))
    # 다른 사용자·다른 scope는 서로의 한도를 소비하지 않는다.
    asyncio.run(agent_quota.enforce_evidence_turn_quota(_request("b")))
    asyncio.run(agent_quota.enforce_novelty_job_quota(_request("a")))

    with pytest.raises(HTTPException):
        asyncio.run(agent_quota.enforce_evidence_turn_quota(_request("a")))


def test_quota_skips_unauthenticated_requests(limiter) -> None:
    # principal은 인증 미들웨어가 세팅한다 — 없으면 라우트의 401이 담당하고 쿼터는 통과.
    asyncio.run(agent_quota.enforce_evidence_turn_quota(_request(None)))
