"""계정 자가 관리 서비스 (FR-28 / BR-A10).

- ``change_password``: 현재 비밀번호 재인증 → BR-A1 정책 검증 → Argon2id 재해싱 →
  **전 세션 무효화**(현 세션 포함; 사용자는 새 비밀번호로 재로그인).
- ``request_email_change``: 새 주소 형식·중복 검사 → 단일사용·30분 토큰(해시 저장) →
  새 주소로 확인 링크 + **현재(기존) 주소로 변경 시도 알림(M2 — 탈취 탐지)**.
  이미 사용 중인 주소로의 변경은 **존재를 노출하지 않기 위해 조용히 무처리**(SEC-BR-2 열거 방지).
- ``confirm_email_change``: 토큰 검증(만료/단일사용) → 확정 시점 선점 재확인(레이스) →
  ``Account.email``(로그인 식별자)을 새 주소로 반영(지연 반영).
"""

import asyncio
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from argon2.exceptions import InvalidHash, VerificationError

from ..integrations.email import EmailClientInterface
from ..models import DomainException, EmailAddress, normalize_email
from ..password import PasswordPolicy, get_password_hasher
from ..repository.credential import CredentialRepository, has_usable_password
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

EMAIL_CHANGE_TOKEN_TTL = timedelta(minutes=30)


def _hash_token(token: str) -> str:
    """변경 확인 토큰의 저장/조회용 SHA-256 해시(평문 비저장·비로깅, SEC-BR-1)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    # 저장된 expires_at(naive UTC)과 동일 기준으로 비교 (password_reset과 일관).
    return datetime.now(UTC).replace(tzinfo=None)


class AccountManagementService:
    def __init__(
        self,
        credential_repo: CredentialRepository,
        session_manager: SessionManager,
        email_client: EmailClientInterface,
    ):
        self._repo = credential_repo
        self._session_manager = session_manager
        self._email_client = email_client
        self._hasher = get_password_hasher()

    async def change_password(self, account_id: str, current_password: str, new_password: str) -> None:
        """현재 비밀번호 재인증 후 새 비밀번호로 교체하고 전 세션을 무효화한다 (BR-A10 §7.1)."""
        account = self._repo.get_by_id(account_id)
        if account is None:
            raise DomainException("계정을 찾을 수 없습니다.")
        if not has_usable_password(account):
            # 소셜-only(비밀번호 없는) 계정 — 비밀번호 변경 대상이 아니다.
            raise DomainException("비밀번호가 설정되지 않은 계정입니다.")
        # 현재 비밀번호 재인증 (CPU 바운드 Argon2는 워커 스레드로 — 이벤트 루프 비차단).
        try:
            verified = await asyncio.to_thread(self._hasher.verify, account.password_hash, current_password)
        except (VerificationError, InvalidHash):
            verified = False
        if not verified:
            raise DomainException("현재 비밀번호가 올바르지 않습니다.")
        # BR-A1 정책 재적용 (실패 시 InvalidPasswordException(=DomainException) 발생).
        PasswordPolicy.evaluate(new_password)
        new_hash = await asyncio.to_thread(self._hasher.hash, new_password)
        account.password_hash = new_hash
        account.failure_count = 0
        account.last_failed_at = None
        self._repo.update_account(account)
        await self._session_manager.invalidate_all_for_user(account.id)  # 전 세션 무효화
        logger.info(f"Password changed for account {account.id}; all sessions invalidated.")

    async def request_email_change(self, account_id: str, new_email: str, confirm_link_base: str) -> None:
        """새 주소로 변경 확인 링크 발송 + 현 주소로 변경 시도 알림(M2). 검증 완료 전까지
        로그인 식별자는 변경하지 않는다(BR-A10 지연 반영)."""
        account = self._repo.get_by_id(account_id)
        if account is None:
            raise DomainException("계정을 찾을 수 없습니다.")
        new_norm = normalize_email(new_email)
        EmailAddress(new_norm)  # 형식 검증 (불량 시 InvalidEmailException(=DomainException)).
        if new_norm == account.email:
            raise DomainException("현재 사용 중인 이메일과 동일합니다.")
        if self._repo.get_by_email(new_norm) is not None:
            # 이미 사용 중 — 계정 존재를 노출하지 않기 위해 조용히 무처리(열거 방지, SEC-BR-2).
            # ponytail: 사용자에겐 동일 일반 응답으로 보이게 컨트롤러가 처리한다.
            logger.info("Email change to an in-use address; silent no-op (non-disclosure).")
            return
        token = secrets.token_urlsafe(32)
        expires_at = _now() + EMAIL_CHANGE_TOKEN_TTL
        self._repo.create_email_change_request(account.id, new_norm, _hash_token(token), expires_at)
        await self._email_client.send_email_change_verification_email(new_norm, token, confirm_link_base)
        # M2: 현재(기존) 이메일로도 변경 시도 알림 — 사일런트 탈취 방지.
        await self._email_client.send_email_change_notice_email(account.email, new_norm)

    async def confirm_email_change(self, token: str) -> None:
        """변경 확인 토큰으로 새 이메일을 로그인 식별자에 반영한다(단일 사용)."""
        if not token:
            raise DomainException("유효하지 않은 확인 토큰입니다.")
        token_hash = _hash_token(token)
        record = self._repo.get_email_change_request(token_hash)
        invalid_msg = "유효하지 않거나 만료된 이메일 변경 링크입니다."
        if record is None:
            raise DomainException(invalid_msg)
        if _now() > record.expires_at:
            self._repo.delete_email_change_request(token_hash)
            raise DomainException(invalid_msg)
        account = self._repo.get_by_id(record.account_id)
        if account is None:
            self._repo.delete_email_change_request(token_hash)
            raise DomainException(invalid_msg)
        # 레이스: 요청~확정 사이에 새 주소가 선점됐으면 거부(유니크 제약 위반 방지).
        taken = self._repo.get_by_email(record.new_email)
        if taken is not None and taken.id != account.id:
            self._repo.delete_email_change_request(token_hash)
            raise DomainException("해당 이메일은 더 이상 사용할 수 없습니다. 다시 시도해 주세요.")
        account.email = record.new_email
        self._repo.update_account(account)
        self._repo.delete_email_change_request(token_hash)  # 단일 사용
        logger.info(f"Email changed for account {account.id}.")
