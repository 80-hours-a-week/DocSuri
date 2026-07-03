from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from backend.app import create_app
from backend.config import Settings
from backend.modules.accounts.models import Principal, UserRole
from backend.modules.novelty.repository import NoveltyJobTable
from backend.modules.research import controller
from backend.modules.research.repository import InMemoryResearchRepository, ResearchJobTable


def _principal(user_id: str | None = None) -> Principal:
    return Principal(user_id=user_id or str(uuid4()), role=UserRole.USER)


def _client(monkeypatch, principal: Principal | None = None, repo=None) -> TestClient:
    monkeypatch.setenv("RESEARCH_AGENT_ENABLED", "true")
    app = create_app(Settings(env="test", database_url="sqlite://"))
    app.dependency_overrides[controller.get_principal] = lambda: principal or _principal()
    if repo is not None:
        app.dependency_overrides[controller.get_repo] = lambda: repo
    return TestClient(app)


def test_research_session_lifecycle(monkeypatch) -> None:
    principal = _principal()
    repo = InMemoryResearchRepository()
    client = _client(monkeypatch, principal, repo)

    created = client.post(
        "/api/research/jobs",
        json={"content": "find evidence for retrieval augmented generation evaluation"},
    )
    job_id = created.json()["jobId"]
    added = client.post(
        f"/api/research/jobs/{job_id}/messages",
        json={"content": "include multi-paper contradiction checks"},
    )
    listed = client.get("/api/research/jobs")
    detail = client.get(f"/api/research/jobs/{job_id}")
    messages = client.get(f"/api/research/jobs/{job_id}/messages")
    deleted = client.delete(f"/api/research/jobs/{job_id}")

    assert created.status_code == 200
    assert added.status_code == 200
    assert listed.json()["jobs"][0]["jobId"] == job_id
    assert detail.json()["job"]["title"].startswith("find evidence")
    assert [item["content"] for item in messages.json()["messages"]] == [
        "find evidence for retrieval augmented generation evaluation",
        "include multi-paper contradiction checks",
    ]
    assert deleted.status_code == 204
    assert client.get(f"/api/research/jobs/{job_id}").status_code == 404


def test_research_sessions_are_owner_scoped(monkeypatch) -> None:
    owner_a = _principal()
    owner_b = _principal()
    repo = InMemoryResearchRepository()
    client_a = _client(monkeypatch, owner_a, repo)
    client_b = _client(monkeypatch, owner_b, repo)

    created = client_a.post("/api/research/jobs", json={"content": "owner scoped session"})
    job_id = created.json()["jobId"]

    assert client_a.get(f"/api/research/jobs/{job_id}").status_code == 200
    assert client_b.get(f"/api/research/jobs/{job_id}").status_code == 404
    assert client_b.get("/api/research/jobs").json()["jobs"] == []


def test_research_job_transitions_to_completed_after_message(monkeypatch) -> None:
    """PR #338 리뷰 Blocking #3 — job.state가 active로 남으면 FE가 이를 running으로
    매핑해 답변이 저장돼도 폴링을 멈추지 않는다."""
    from backend.modules.research.models import ResearchJobState

    principal = _principal()
    repo = InMemoryResearchRepository()
    client = _client(monkeypatch, principal, repo)

    created = client.post("/api/research/jobs", json={"content": "test question"})
    assert created.json()["state"] == ResearchJobState.COMPLETED.value

    job_id = created.json()["jobId"]
    detail = client.get(f"/api/research/jobs/{job_id}")
    assert detail.json()["job"]["state"] == ResearchJobState.COMPLETED.value

    followup = client.post(
        f"/api/research/jobs/{job_id}/messages", json={"content": "follow-up"}
    )
    assert followup.status_code == 200
    detail_after_followup = client.get(f"/api/research/jobs/{job_id}")
    assert detail_after_followup.json()["job"]["state"] == ResearchJobState.COMPLETED.value


def test_sql_repositories_bind_postgres_uuid_ids() -> None:
    dialect = postgresql.dialect()

    for table in (ResearchJobTable, NoveltyJobTable):
        stmt = table.__table__.select().where(
            table.owner_id == "00000000-0000-0000-0000-000000000001"
        )
        compiled = stmt.compile(dialect=dialect, compile_kwargs={"render_postcompile": True})

        assert table.__table__.c.owner_id.type.compile(dialect=dialect) == "UUID"
        assert "::UUID" in str(compiled)
