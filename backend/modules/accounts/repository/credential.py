from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session, declarative_base

from ..models import AccountStatus, DomainException

Base = declarative_base()

class AccountTable(Base):
    __tablename__ = "accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(254), unique=True, nullable=False, index=True)
    # U10: Google/ORCID 전용 가입(비밀번호 미설정)을 허용하므로 NOT NULL 제약을 제거했다.
    password_hash = Column(String(255), nullable=True)
    status = Column(String(20), default=AccountStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_failed_at = Column(DateTime, nullable=True)
    # BR-A7: 역할 단일 출처는 DB(공개 가입=USER; ADMIN은 시딩만). totp_secret은 MFA 등록 시 채워진다.
    role = Column(String(20), default="USER", nullable=False)
    totp_secret = Column(String(64), nullable=True)
    # U10: Google/ORCID 소셜로그인 연동 — 기존 이메일+비밀번호 로그인과 공존한다(연동 해제해도
    # 로그인 수단이 사라지지 않음). 두 식별자 모두 계정당 유일해야 하므로 unique=True.
    google_sub = Column(String(255), unique=True, nullable=True)
    google_linked_at = Column(DateTime, nullable=True)
    orcid_id = Column(String(19), unique=True, nullable=True)
    orcid_linked_at = Column(DateTime, nullable=True)
    # ORCID record(이름/소속) 캐시 — works(논문 목록)는 1:N이라 컬럼에 두지 않고 조회 시마다
    # ORCID API에서 다시 가져온다.
    orcid_name = Column(String(255), nullable=True)
    orcid_affiliation = Column(String(255), nullable=True)
    orcid_synced_at = Column(DateTime, nullable=True)
    # 탈퇴(soft-delete) 여부는 status 값으로 추론하지 않고 별도 bool 컬럼으로 명시 판단한다.
    is_withdrawn = Column(Boolean, default=False, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)


class VerificationTokenTable(Base):
    __tablename__ = "verification_tokens"

    token = Column(String(64), primary_key=True)
    email = Column(String(254), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)


class AccountWithdrawalBackupTable(Base):
    """U10 회원탈퇴 시점의 accounts 스냅샷 (5년 보관, purge_after 이후 하드 삭제 대상).

    U3가 소유한 데이터만 담는다 — 라이브러리(U4)/행동 이벤트·관심 프로필(U9)은 1:N 데이터라
    여기 담을 수 없고 각 모듈이 별도로 백업해야 한다(후속 작업). password_hash/totp_secret은
    재로그인 복구 목적이 아니므로 의도적으로 제외한다."""

    __tablename__ = "account_withdrawal_backups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_account_id = Column(String(36), nullable=False, index=True)
    email = Column(String(254), nullable=False)
    status = Column(String(20), nullable=False)
    google_sub = Column(String(255), nullable=True)
    orcid_id = Column(String(19), nullable=True)
    orcid_name = Column(String(255), nullable=True)
    orcid_affiliation = Column(String(255), nullable=True)
    signed_up_at = Column(DateTime, nullable=False)
    withdrawn_at = Column(DateTime, nullable=False)
    purge_after = Column(DateTime, nullable=False, index=True)
    backed_up_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CredentialRepository:
    """SQLAlchemy 기반의 Credential 및 계정 영속성 저장소 (PostgreSQL 매핑)"""
    
    def __init__(self, db_session: Session):
        self._session = db_session
        # 타이밍 공격 방어용 더미 해시 (argon2 KDF로 미리 만들어둔 일반적인 형태의 더미 값)
        # 실제 계정이 없을 때 이 더미 해시와 입력 패스워드를 대조 연산함으로써 시간 유추를 불가능하게 함
        self.dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$abcdefghijklmnopqrstuvwxyz0123456789abcd"

    def get_by_email(self, email: str) -> AccountTable | None:
        """이메일로 계정을 조회합니다."""
        return self._session.query(AccountTable).filter(AccountTable.email == email).first()

    def get_by_id(self, account_id: str) -> AccountTable | None:
        """식별자로 계정을 조회합니다."""
        return self._session.query(AccountTable).filter(AccountTable.id == account_id).first()

    def create_account(self, email: str, password_hash: str) -> AccountTable:
        """
        신규 계정을 생성합니다.
        verify-all-then-commit 원칙에 따라, 본 메서드는 DB 메모리에 기록만 수행하며
        실제 commit은 서비스 레이어의 검증이 모두 끝난 최종 시점에 외부 세션에 의해 수행됩니다.
        """
        # 이메일 중복 최종 확인
        existing = self.get_by_email(email)
        if existing:
            raise DomainException("이미 등록된 이메일 주소입니다.")

        account = AccountTable(
            id=str(uuid4()),
            email=email,
            password_hash=password_hash,
            status=AccountStatus.PENDING.value,
            created_at=datetime.now(UTC),
            failure_count=0
        )
        self._session.add(account)
        self._session.flush() # ID 등 임시 생성을 위해 메모리 플러시
        return account

    def update_account(self, account: AccountTable) -> None:
        """계정 정보를 업데이트합니다. (실패 횟수 누적, 상태 변경, 해시 재설정 등)"""
        self._session.add(account)
        self._session.flush()

    def create_verification_token(self, email: str, token: str, expires_at: datetime) -> VerificationTokenTable:
        """이메일 인증 토큰을 생성합니다."""
        # 기존 해당 이메일의 만료된 토큰이 있다면 삭제
        self._session.query(VerificationTokenTable).filter(VerificationTokenTable.email == email).delete()
        
        token_record = VerificationTokenTable(
            token=token,
            email=email,
            expires_at=expires_at
        )
        self._session.add(token_record)
        self._session.flush()
        return token_record

    def get_verification_token(self, token: str) -> VerificationTokenTable | None:
        """토큰 값으로 이메일 인증 토큰 레코드를 조회합니다."""
        return self._session.query(VerificationTokenTable).filter(VerificationTokenTable.token == token).first()

    def delete_verification_token(self, token: str) -> None:
        """인증 완료 후 사용한 이메일 인증 토큰을 파기합니다."""
        self._session.query(VerificationTokenTable).filter(VerificationTokenTable.token == token).delete()
        self._session.flush()
