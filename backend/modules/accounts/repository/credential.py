from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session, declarative_base

from ..models import AccountStatus, DomainException

Base = declarative_base()

class AccountTable(Base):
    __tablename__ = "accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default=AccountStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_failed_at = Column(DateTime, nullable=True)


class VerificationTokenTable(Base):
    __tablename__ = "verification_tokens"
    
    token = Column(String(64), primary_key=True)
    email = Column(String(254), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)


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
            created_at=datetime.utcnow(),
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
