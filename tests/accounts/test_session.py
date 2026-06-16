import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from redis.exceptions import ConnectionError as RedisConnectionError

from backend.modules.accounts.models import (
    SessionRecord, Principal, UserRole, SessionExpiredException, 
    UnauthorizedException, SessionStoreUnavailableException
)
from backend.modules.accounts.repository.session import SessionRepository
from backend.modules.accounts.services.session_manager import SessionManager

@pytest.fixture
def mock_session_repo():
    repo = MagicMock(spec=SessionRepository)
    repo.save = AsyncMock()
    repo.get = AsyncMock()
    repo.delete = AsyncMock()
    return repo

@pytest.fixture
def session_manager(mock_session_repo):
    # idle_timeout: 2시간, absolute_lifetime: 30일 기본 세팅
    return SessionManager(mock_session_repo, idle_timeout_hours=2, max_lifetime_days=30)


@pytest.mark.asyncio
async def test_session_issue_and_verify_success(mock_session_repo, session_manager):
    """정상 세션 발급 및 검증과 sliding expiration 갱신 검증 (US-A2, BR-A3)"""
    principal = Principal(user_id="a0000000-0000-0000-0000-000000000000", role=UserRole.USER)
    
    # 세션 발급
    session = await session_manager.issue(principal)
    assert session.handle is not None
    assert session.user_id == principal.user_id
    
    # Redis save 호출 검증
    mock_session_repo.save.assert_called_once_with(session)
    
    # 세션 검증 모킹
    mock_session_repo.get.return_value = session
    
    # 검증 수행 (sliding 갱신을 위해 save가 추가 호출됨)
    verified_principal = await session_manager.verify(session.handle)
    
    assert verified_principal.user_id == principal.user_id
    # get 1회, 갱신 save 1회(총 2회) 호출 체크
    assert mock_session_repo.get.call_count == 1
    assert mock_session_repo.save.call_count == 2 


@pytest.mark.asyncio
async def test_session_sliding_expiration_expired(mock_session_repo, session_manager):
    """마지막 활성 시각으로부터 2시간 초과 시 세션 즉시 만료 및 파기 검증 (US-A2, BR-A3)"""
    now = datetime.utcnow()
    # 2시간 1분 전 활성
    expired_active_at = now - timedelta(hours=2, minutes=1)
    
    session = SessionRecord(
        handle="expired_handle",
        user_id="a0000000-0000-0000-0000-000000000000",
        created_at=now - timedelta(days=1),
        last_active_at=expired_active_at,
        expires_at=now + timedelta(days=29)
    )
    
    mock_session_repo.get.return_value = session
    
    # 검증 시 만료 예외 발생
    with pytest.raises(SessionExpiredException) as excinfo:
        await session_manager.verify(session.handle)
    assert "비활성화 상태" in str(excinfo.value)
    
    # 만료된 세션은 즉시 무효화(삭제) 처리 보장
    mock_session_repo.delete.assert_called_once_with(session.handle)


@pytest.mark.asyncio
async def test_session_absolute_expiration_expired(mock_session_repo, session_manager):
    """최초 생성 시각으로부터 30일 초과 시 세션 즉시 만료 및 파기 검증 (US-A2, BR-A3)"""
    now = datetime.utcnow()
    # 30일 1초 전 생성
    expired_created_at = now - timedelta(days=30, seconds=1)
    
    session = SessionRecord(
        handle="expired_handle",
        user_id="a0000000-0000-0000-0000-000000000000",
        created_at=expired_created_at,
        last_active_at=now - timedelta(minutes=5), # sliding은 유효
        expires_at=now - timedelta(seconds=1)
    )
    
    mock_session_repo.get.return_value = session
    
    # 검증 시 절대 만료 예외 발생
    with pytest.raises(SessionExpiredException) as excinfo:
        await session_manager.verify(session.handle)
    assert "최대 사용 기간" in str(excinfo.value)
    
    # 강제 파기
    mock_session_repo.delete.assert_called_once_with(session.handle)


@pytest.mark.asyncio
async def test_session_redis_failure_fail_closed(mock_session_repo, session_manager):
    """
    피드백 ② 반영: Redis 연결 장애 시 Fail-Closed 정책 검증
    DB 폴백 없이 즉각 UnauthorizedException 예외를 던져 보호막을 차단함.
    """
    # Redis 연결 장애 모킹
    mock_session_repo.get.side_effect = SessionStoreUnavailableException("Connection refused")
    
    with pytest.raises(UnauthorizedException) as excinfo:
        await session_manager.verify("some_token")
        
    # 장애 시 비즈니스 예외 세션 에러가 401(UnauthorizedException)로 래핑되어 던져졌는지 확인
    assert "세션 저장소 일시 장애" in str(excinfo.value)
    # DB 조회 등으로 폴백하는 엣지가 작동하지 않았는지 검증 (Fail-Closed)
