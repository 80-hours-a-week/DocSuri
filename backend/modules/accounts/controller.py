import os
from functools import lru_cache
from fastapi import APIRouter, Depends, Request, Response, HTTPException, Header, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .schemas import SignupRequest, SignupResult, LoginRequest, SessionInfo
from .models import DomainException, UnauthorizedException, SessionExpiredException, SessionStoreUnavailableException
from .services.signup import SignupService
from .services.auth import AuthenticationService
from .services.session_manager import SessionManager
from .repository.credential import CredentialRepository
from .repository.session import SessionRepository
from .integrations.email import get_email_client
from .integrations.recaptcha import RecaptchaClient

router = APIRouter(prefix="/auth", tags=["Accounts/Auth"])

# DB 세션 디펜던시 스텁 (메인 App shell에서 오버라이드 예정)
def get_db_session() -> Session:
    raise NotImplementedError("Database session dependency must be overridden by app shell")

# 레포지토리 및 서비스 조립 디펜던시
def get_credential_repo(db: Session = Depends(get_db_session)) -> CredentialRepository:
    return CredentialRepository(db)

# 세션 저장소는 프로세스 단위 싱글톤으로 구성한다.
# 요청마다 SessionRepository()를 새로 만들면 그때마다 Redis ConnectionPool(max_connections=50)이
# 생성되어 커넥션 처닝/고갈을 유발하므로, lru_cache로 단일 인스턴스를 재사용한다.
# 풀 teardown은 App shell의 shutdown 이벤트에서 SessionRepository.close()로 1회 수행한다.
@lru_cache(maxsize=1)
def get_session_repo() -> SessionRepository:
    return SessionRepository()

def get_recaptcha_client() -> RecaptchaClient:
    secret_key = os.getenv("RECAPTCHA_SECRET_KEY", "")
    return RecaptchaClient(secret_key=secret_key)

def get_session_manager(repo: SessionRepository = Depends(get_session_repo)) -> SessionManager:
    return SessionManager(repo)

def get_signup_service(
    repo: CredentialRepository = Depends(get_credential_repo),
) -> SignupService:
    # 메인 App Shell 또는 DI 컨테이너에서 설정 주입. default는 로컬 모킹 클라이언트
    email_client = get_email_client(env=os.getenv("ENV", "local"))
    return SignupService(repo, email_client)

def get_auth_service(
    repo: CredentialRepository = Depends(get_credential_repo),
    manager: SessionManager = Depends(get_session_manager),
    recaptcha: RecaptchaClient = Depends(get_recaptcha_client)
) -> AuthenticationService:
    return AuthenticationService(repo, manager, recaptcha)


@router.post("/signup", response_model=SignupResult, status_code=201)
async def signup(
    req: SignupRequest,
    request: Request,
    signup_svc: SignupService = Depends(get_signup_service),
    db: Session = Depends(get_db_session)
):
    """
    일반 사용자 공개 회원가입 (US-A1)
    가입 성공 시 PENDING 계정이 생성되며 이메일 인증 발송 처리됩니다.
    """
    # 호스트 이름을 동적으로 파악해 메일 인증용 베이스 링크 생성
    base_url = str(request.base_url) + "auth/verify-email"

    try:
        account_id = await signup_svc.register(
            email=req.email,
            password=req.password,
            verification_link_base=base_url
        )
        # verify-all-then-commit: 컨트롤러 엔드포인트 도달 완료 시점에만 세션 최종 commit 강제
        db.commit()
        # 필드명으로 생성한다. 직렬화 시 serialization_alias 로 'accountId' 키가 출력된다.
        return SignupResult(account_id=account_id)

    except DomainException as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="회원가입 처리 중 알 수 없는 장애가 발생했습니다. (Fail-Closed)")


@router.post("/login")
async def login(
    response: Response,
    req: LoginRequest,
    x_recaptcha_token: str | None = Header(None, alias="X-Recaptcha-Token"),
    auth_svc: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db_session)
):
    """
    사용자 로그인 및 세션 쿠키 발급 (US-A2)
    인증 성공 시 Sliding(2시간) / Absolute(30일) 만료 속성의 보안 쿠키를 클라이언트에 바인딩합니다.
    """
    try:
        # 인증 검증 및 세션 토큰 획득 (내부에서 reCAPTCHA, 실패 지연, 해시 업그레이드 제어)
        session_handle = await auth_svc.authenticate(
            email=req.email,
            password=req.password,
            recaptcha_token=x_recaptcha_token
        )
        db.commit() # 실패 카운트 리셋 등 계정 상태 커밋

        # SEC-12: 보안 세션 토큰은 body DTO가 아닌 httpOnly 쿠키로만 외부 전송
        response.set_cookie(
            key="session_id",
            value=session_handle,
            httponly=True,
            secure=True,          # HTTPS 환경 강제
            samesite="lax",       # CORS CSRF 완화 정책 적용
            max_age=30 * 24 * 60 * 60 # 30일 절대 만료 세션
        )

        return {"status": "success", "message": "로그인에 성공했습니다."}

    except DomainException as e:
        db.rollback()
        # 자격증명 비노출(SEC-BR-2): "이메일 또는 비밀번호가 올바르지 않습니다." 등으로 일반화된 401 반환
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="인증 처리 중 서버 장애가 발생했습니다. (Fail-Closed)")


@router.get("/verify-email")
async def verify_email(
    token: str = Query(..., description="이메일 활성화 토큰"),
    signup_svc: SignupService = Depends(get_signup_service),
    db: Session = Depends(get_db_session)
):
    """PENDING 계정 가입 메일 링크 인증 엔드포인트 (US-A1, BR-A5)"""
    try:
        await signup_svc.verify_email(token)
        db.commit()
        return {"status": "success", "message": "이메일 인증이 성공적으로 완료되었습니다. 이제 로그인할 수 있습니다."}
    except DomainException as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="이메일 검증 처리 중 서버 장애가 발생했습니다.")


@router.get("/session", response_model=SessionInfo)
async def get_session(
    request: Request,
    session_mgr: SessionManager = Depends(get_session_manager),
):
    """현재 세션의 유효성 검증 및 정보 조회 (Sliding Expiration 갱신 연동) (US-A2, BR-A3)"""
    # 쿠키로부터 세션 토큰 추출
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    try:
        # verify() 호출 시 내부적으로 sliding 만료 갱신 및 만료 검증 강제
        principal = await session_mgr.verify(session_id)

        # 30일 절대만료 시점 또는 sliding 2시간 만료 시점 제공
        # 여기서는 편의상 sliding 2시간 만료 시점으로 expiresAt 반환
        expires_at = datetime.utcnow() + timedelta(hours=2)

        # 필드명으로 생성한다. 직렬화 시 serialization_alias 로 'userId'/'expiresAt' 키가 출력된다.
        return SessionInfo(user_id=principal.user_id, expires_at=expires_at)

    except (UnauthorizedException, SessionExpiredException) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="세션 검증 중 서버 오류가 발생했습니다. (Fail-Closed)")


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_mgr: SessionManager = Depends(get_session_manager),
):
    """현재 세션을 수동 파기하고 보안 쿠키를 삭제합니다."""
    session_id = request.cookies.get("session_id")
    if session_id:
        try:
            await session_mgr.invalidate(session_id)
        except Exception:
            pass # 로그아웃 예외는 무시하고 클라이언트 쿠키 클리어 진행

    response.delete_cookie(key="session_id")
    return {"status": "success", "message": "로그아웃되었습니다."}
