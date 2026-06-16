import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.modules.accounts.repository.credential import Base, CredentialRepository, AccountTable, VerificationTokenTable
from backend.modules.accounts.models import DomainException, AccountStatus, UserRole, Principal
from backend.modules.accounts.services.signup import SignupService
from backend.modules.accounts.services.auth import AuthenticationService
from backend.modules.accounts.services.session_manager import SessionManager
from backend.modules.accounts.integrations.email import MockEmailClient
from backend.modules.accounts.integrations.recaptcha import RecaptchaClient

# 인메모리 SQLite DB를 활용하여 가볍고 독립적인 DB 세션 통합 환경 구성
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()

@pytest.fixture
def credential_repo(db_session):
    return CredentialRepository(db_session)

@pytest.fixture
def email_client():
    return MockEmailClient()

@pytest.fixture
def session_manager():
    # SessionManager 및 Redis Repository 모킹
    manager = MagicMock(spec=SessionManager)
    manager.issue = AsyncMock()
    return manager

@pytest.fixture
def recaptcha_client():
    client = MagicMock(spec=RecaptchaClient)
    client.verify_token = AsyncMock(return_value=True)
    return client

@pytest.fixture
def mock_observability():
    hub = MagicMock()
    hub.emitMetric = MagicMock()
    hub.emitLog = MagicMock()
    return hub


@pytest.mark.asyncio
async def test_signup_flow_success(credential_repo, email_client, mock_observability, db_session):
    """정상 가입 요청 시 PENDING 상태 등록 및 토큰 검증 후 ACTIVE 전환 검증 (US-A1, BR-A5)"""
    service = SignupService(
        credential_repo=credential_repo,
        email_client=email_client,
        observability_hub=mock_observability
    )

    # 1. 회원가입 신청
    email = "test@docsuri.dev"
    password = "SecurePass123!" # 복잡도 충족
    verification_link = "https://localhost/auth/verify-email"
    
    account_id = await service.register(email, password, verification_link)
    db_session.commit()
    
    assert account_id is not None

    # 가입 직후 PENDING 상태 확인
    account = credential_repo.get_by_id(account_id)
    assert account.status == AccountStatus.PENDING.value
    assert account.email == email
    assert account.failure_count == 0

    # 2. 이메일 토큰 조회 및 검증
    token_record = db_session.query(VerificationTokenTable).filter(VerificationTokenTable.email == email).first()
    assert token_record is not None
    
    # 이메일 검증 처리 진행
    verified = await service.verify_email(token_record.token)
    db_session.commit()
    
    assert verified is True
    
    # 활성화 상태 및 토큰 소멸 확인
    account = credential_repo.get_by_id(account_id)
    assert account.status == AccountStatus.ACTIVE.value
    
    token_record_after = db_session.query(VerificationTokenTable).filter(VerificationTokenTable.token == token_record.token).first()
    assert token_record_after is None


@pytest.mark.asyncio
async def test_signup_invalid_password(credential_repo, email_client):
    """비밀번호 복잡도 요건 미달 시 회원가입이 즉각 차단되는지 검증 (US-A1, BR-A1)"""
    service = SignupService(credential_repo=credential_repo, email_client=email_client)

    # 대문자 결여 및 10자 미만 비밀번호
    with pytest.raises(DomainException) as excinfo:
        await service.register("test@docsuri.dev", "weak123!", "http://localhost")
    assert "비밀번호는 최소 10자 이상이어야 합니다" in str(excinfo.value)


@pytest.mark.asyncio
async def test_authentication_backoff_on_failure(credential_repo, session_manager, recaptcha_client, mock_observability, db_session):
    """로그인 3회 이상 실패 시 지수 백오프 비동기 지연(asyncio.sleep)이 작동하는지 검증 (US-A2, BR-A4)"""
    auth_service = AuthenticationService(
        credential_repo=credential_repo,
        session_manager=session_manager,
        recaptcha_client=recaptcha_client,
        observability_hub=mock_observability
    )
    
    # 계정 사전 생성 및 ACTIVE 활성화
    email = "user@docsuri.dev"
    password = "ValidPassword123!"
    
    # 가입
    signup_svc = SignupService(credential_repo, MockEmailClient())
    account_id = await signup_svc.register(email, password, "http://localhost")
    account = credential_repo.get_by_id(account_id)
    account.status = AccountStatus.ACTIVE.value
    credential_repo.update_account(account)
    db_session.commit()

    # 1. 1~2회 로그인 실패 시 지연 없음
    with pytest.raises(DomainException):
        await auth_service.authenticate(email, "WrongPassword1!")
    assert credential_repo.get_by_id(account_id).failure_count == 1

    with pytest.raises(DomainException):
        await auth_service.authenticate(email, "WrongPassword1!")
    assert credential_repo.get_by_id(account_id).failure_count == 2

    # 2. 3회 로그인 실패 시 백오프 지연 적용 (2^(3-3) = 1초)
    # asyncio.sleep() 호출을 모킹하여 스레드가 차단되지 않음을 추적
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(DomainException):
            await auth_service.authenticate(email, "WrongPassword1!")
        
        # 3회 실패 시 2^0 = 1초 지연 호출 감지
        mock_sleep.assert_called_once_with(1)
        assert credential_repo.get_by_id(account_id).failure_count == 3


@pytest.mark.asyncio
async def test_authentication_recaptcha_enforcement(credential_repo, session_manager, recaptcha_client, db_session):
    """로그인 10회 실패 시 reCAPTCHA 검증 요구 및 Fail-Closed 작동 검증 (US-A2, BR-A4)"""
    auth_service = AuthenticationService(
        credential_repo=credential_repo,
        session_manager=session_manager,
        recaptcha_client=recaptcha_client,
        observability_hub=MagicMock()
    )
    
    email = "bot@docsuri.dev"
    password = "ValidPassword123!"
    
    signup_svc = SignupService(credential_repo, MockEmailClient())
    account_id = await signup_svc.register(email, password, "http://localhost")
    account = credential_repo.get_by_id(account_id)
    account.status = AccountStatus.ACTIVE.value
    # 실패 카운트 강제 10회 주입
    account.failure_count = 10
    credential_repo.update_account(account)
    db_session.commit()

    # 토큰 없이 로그인 시도 시 즉각 에러
    with pytest.raises(DomainException) as excinfo:
        await auth_service.authenticate(email, password)
    assert "CAPTCHA" in str(excinfo.value)

    # 토큰 검증 실패 모킹 시 거부 (Fail-Closed)
    recaptcha_client.verify_token.return_value = False
    with pytest.raises(DomainException) as excinfo:
        await auth_service.authenticate(email, password, recaptcha_token="bad_token")
    assert "CAPTCHA" in str(excinfo.value)

    # 토큰 검증 통과 시 로그인 허용
    recaptcha_client.verify_token.return_value = True
    session_manager.issue.return_value = MagicMock(handle="test_session_token")
    
    token = await auth_service.authenticate(email, password, recaptcha_token="good_token")
    assert token == "test_session_token"
