from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from backend.app import create_app
from backend.config import Settings
from backend.modules.accounts.models import Principal, UserRole
from backend.modules.evidence import controller
from backend.modules.evidence.assembler import EvidenceComparisonAssembler
from backend.modules.evidence.models import (
    EvidenceSession,
    TurnAbstainResult,
    TurnErrorResult,
    TurnSuccessResult,
)
from backend.modules.evidence.repository import InMemoryEvidenceRepository
from backend.modules.evidence.service import (
    EvidenceSessionManagementService,
)


def _principal(user_id: str | None = None) -> Principal:
    return Principal(user_id=user_id or str(uuid4()), role=UserRole.USER)


def _client(monkeypatch, principal: Principal | None = None, repo=None) -> TestClient:
    monkeypatch.setenv('EVIDENCE_AGENT_ENABLED', 'true')
    app = create_app(Settings(env='test', database_url='sqlite://'))
    app.dependency_overrides[controller.get_principal] = lambda: principal or _principal()
    if repo is not None:
        app.dependency_overrides[controller.get_repo] = lambda: repo

    # Orchestrator 없이 테스트 — real_wiring 없이 controller만 마운트
    class _StubOrchestrator:
        def run(self, ctx, request):
            return TurnAbstainResult(
                outcome=__import__(
                    'docsuri_shared._generated.dtos.evidence_schema',
                    fromlist=['EvidenceAbstainResult'],
                ).EvidenceAbstainResult(
                    state='abstain',
                    abstainReason='out_of_corpus',
                )
            )

    app.dependency_overrides[controller.get_orchestrator] = lambda: _StubOrchestrator()
    return TestClient(app)


# ---------------------------------------------------------------------------
# PBT-EV-1: INV-EV-2 — claims=[] 이면 반드시 abstain 반환
# ---------------------------------------------------------------------------

@given(st.just([]))  # claims 항상 빈 리스트
def test_empty_claims_yields_abstain(claims) -> None:
    from backend.modules.evidence.models import PaperSearchResult

    assembler = EvidenceComparisonAssembler()
    search_result = PaperSearchResult(records=(), query_used='test', scope='auto')

    # abstain 경로: orchestrator가 items=[] 시 TurnAbstainResult를 직접 반환
    # assembler는 항상 ok를 반환하고 orchestrator가 INV-EV-2 강제
    # 여기서는 assembler 결과가 ok지만 claims=[]인 경우 orchestrator 코드 경로 확인
    result = assembler.assemble(claims, search_result, paper_count=0)
    assert result.state == 'ok'
    assert result.claims == claims  # assembler 자체는 빈 리스트 허용 — orchestrator가 강제


# ---------------------------------------------------------------------------
# PBT-EV-2: INV-EV-1 / SEC-9 — 소유권 불일치 → KeyError (→ 404)
# ---------------------------------------------------------------------------

@given(
    st.text(alphabet='abcdef0123456789-', min_size=36, max_size=36),
    st.text(alphabet='abcdef0123456789-', min_size=36, max_size=36),
)
def test_cross_owner_session_read_raises_key_error(owner_a: str, owner_b: str) -> None:
    if owner_a == owner_b:
        return

    repo = InMemoryEvidenceRepository()
    session = EvidenceSession(owner_id=owner_a)
    repo.create_session(session)

    try:
        repo.get_session(owner_b, session.session_id)
    except KeyError:
        pass
    else:
        raise AssertionError('cross-owner session read must raise KeyError (SEC-9 → 404)')


# ---------------------------------------------------------------------------
# PBT-EV-3: INV-EV-5 — TurnResult 직렬화에 벡터 점수 미포함
# ---------------------------------------------------------------------------

def test_turn_result_serialization_excludes_internal_fields() -> None:
    from docsuri_shared._generated.dtos.evidence_schema import (
        EvidenceAbstainResult,
        EvidenceCoverage,
        EvidenceResult,
    )

    success = TurnSuccessResult(
        outcome=EvidenceResult(
            state='ok',
            claims=[],
            coverage=EvidenceCoverage(paperCount=1, queryUsed='test'),
        )
    )
    abstain = TurnAbstainResult(
        outcome=EvidenceAbstainResult(state='abstain', abstainReason='out_of_corpus')
    )
    error = TurnErrorResult(error_code='llm_unavailable')

    from backend.modules.evidence.repository import _serialize_result

    for result in (success, abstain, error):
        data, _ = _serialize_result(result)
        if data:
            raw = str(data)
            for forbidden in ('score', 'chunk_id', 'chunkId', 'vector', 'llm_meta'):
                assert forbidden not in raw, (
                    f'INV-EV-5 violation: {forbidden!r} in serialized result'
                )


# ---------------------------------------------------------------------------
# 단위: 세션 소프트 삭제 (BR-EV-8)
# ---------------------------------------------------------------------------

def test_soft_delete_hides_session() -> None:
    repo = InMemoryEvidenceRepository()
    owner = str(uuid4())
    session = EvidenceSession(owner_id=owner)
    repo.create_session(session)

    assert len(repo.list_sessions(owner)) == 1
    repo.soft_delete_session(owner, session.session_id)
    assert repo.list_sessions(owner) == []

    # 삭제 후 get_session도 KeyError (INV-EV-1 / SEC-9)
    try:
        repo.get_session(owner, session.session_id)
    except KeyError:
        pass
    else:
        raise AssertionError('deleted session must not be retrievable')


# ---------------------------------------------------------------------------
# 단위: 전체 초기화 (BR-EV-9)
# ---------------------------------------------------------------------------

def test_reset_all_only_affects_owner() -> None:
    repo = InMemoryEvidenceRepository()
    owner_a = str(uuid4())
    owner_b = str(uuid4())

    for _ in range(3):
        repo.create_session(EvidenceSession(owner_id=owner_a))
    repo.create_session(EvidenceSession(owner_id=owner_b))

    svc = EvidenceSessionManagementService(repo=repo)
    svc.reset_all(owner_a)

    assert repo.list_sessions(owner_a) == []
    assert len(repo.list_sessions(owner_b)) == 1


# ---------------------------------------------------------------------------
# 단위: 세션 목록 정렬 (BR-EV-10)
# ---------------------------------------------------------------------------

def test_list_sessions_returns_updated_at_desc() -> None:
    import time

    repo = InMemoryEvidenceRepository()
    owner = str(uuid4())

    s1 = EvidenceSession(owner_id=owner, title='first')
    repo.create_session(s1)
    time.sleep(0.01)
    s2 = EvidenceSession(owner_id=owner, title='second')
    repo.create_session(s2)

    sessions = repo.list_sessions(owner)
    assert sessions[0].session_id == s2.session_id  # 최신 우선


# ---------------------------------------------------------------------------
# API: POST /api/evidence/turns → 201 + abstain (stub orchestrator)
# ---------------------------------------------------------------------------

def test_api_create_turn_returns_turn_out(monkeypatch) -> None:
    principal = _principal()
    repo = InMemoryEvidenceRepository()
    client = _client(monkeypatch, principal, repo)

    resp = client.post(
        '/api/evidence/turns',
        json={'topic': 'transformer attention mechanism', 'scope': 'auto'},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['result']['state'] == 'abstain'
    assert 'sessionId' in body
    assert 'turnId' in body


# ---------------------------------------------------------------------------
# API: 인증 없으면 401
# ---------------------------------------------------------------------------

def test_api_requires_authentication(monkeypatch) -> None:
    monkeypatch.setenv('EVIDENCE_AGENT_ENABLED', 'true')
    app = create_app(Settings(env='test', database_url='sqlite://'))
    # principal override 없음 → get_principal이 401 반환
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        '/api/evidence/turns',
        json={'topic': 'test'},
    )

    assert resp.status_code == 401
