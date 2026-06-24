"""계정 삭제 — 소프트 삭제 + 유예 비동기 파기 (FR-28 / BR-A11).

2상 삭제:
  ① 동기 소프트 삭제(``request_deletion``): ``DEACTIVATED`` 전이 + 전 세션 즉시 무효화(로그인
     차단) + 삭제 레코드(``purge_after``) 생성. **이 시점에 owner-scoped 데이터를 보존**(복구
     가능) — ``AccountDeleted``는 발행하지 않는다(H2).
  ② 비동기 유예 파기(``purge_job``): ``purge_after`` 경과분을 일괄 처리. 각 계정에 대해
     **``AccountDeleted`` 이벤트 발행**(U4/U2/U11이 구독해 각자 owner-scoped 파기 — 직접 호출
     아님, 코드 DAG 비순환) → 자격증명 영구 삭제 → ``PURGED`` 전이(멱등).

유예 중 ``reactivate``(소유자 복구, M1) 가능.

실제 EventBridge 발행 트랜스포트는 인프라 슬라이스로 이월하고(FR-27 OIDC 트랜스포트 분리와
동일 패턴), 코어 파기 로직은 발행자 포트로 분리해 단위 테스트 가능하게 둔다.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol

from ..models import AccountStatus, DomainException
from ..repository.credential import CredentialRepository
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

DEFAULT_GRACE_DAYS = 30  # 유예 기간 N (events.md 기본 제안 30일; 운영/법적 요건으로 조정).


class AccountDeletedPublisher(Protocol):
    """``AccountDeleted`` 캐스케이드 이벤트 발행자 포트 (shared/events.md 계약)."""

    async def publish(self, account_id: str, occurred_at: datetime, event_id: str) -> None: ...


class LoggingAccountDeletedPublisher:
    """기본 발행자 — 구조화 로그로만 기록한다. 실 EventBridge 트랜스포트는 인프라 슬라이스로 이월.
    멱등 키는 ``account_id``, 중복 식별 키는 ``event_id``(at-least-once)다."""

    async def publish(self, account_id: str, occurred_at: datetime, event_id: str) -> None:
        logger.info(
            {
                "event": "AccountDeleted",
                "accountId": account_id,
                "occurredAt": occurred_at.isoformat(),
                "eventId": event_id,
            }
        )


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AccountDeletionService:
    def __init__(
        self,
        credential_repo: CredentialRepository,
        session_manager: SessionManager,
        publisher: AccountDeletedPublisher | None = None,
        grace_days: int = DEFAULT_GRACE_DAYS,
    ):
        self._repo = credential_repo
        self._session_manager = session_manager
        self._publisher = publisher or LoggingAccountDeletedPublisher()
        self._grace_days = grace_days

    async def request_deletion(self, account_id: str) -> None:
        """소프트 삭제: DEACTIVATED 전이 + 전 세션 무효화 + 유예 레코드 생성 (멱등)."""
        account = self._repo.get_by_id(account_id)
        if account is None:
            raise DomainException("계정을 찾을 수 없습니다.")
        account.status = AccountStatus.DEACTIVATED.value
        self._repo.update_account(account)
        purge_after = _now() + timedelta(days=self._grace_days)
        self._repo.create_account_deletion(account.id, purge_after)  # 멱등: 기존 미파기 레코드 재사용
        await self._session_manager.invalidate_all_for_user(account.id)  # 즉시 로그인 차단
        # SEC-14: 추가전용 감사 로그(구조화 로그로 기록; 전용 감사 스토어는 인프라 이월).
        logger.info({"event": "AccountDeactivated", "accountId": account.id, "purgeAfter": purge_after.isoformat()})
        # H2: AccountDeleted는 여기서 발행하지 않는다(유예 동안 데이터 보존·복구 가능).

    async def reactivate(self, account_id: str) -> None:
        """유예 중 소유자 재활성화(복구): DEACTIVATED→ACTIVE, 삭제 레코드 제거 (M1)."""
        rec = self._repo.get_account_deletion(account_id)
        if rec is None or rec.state != AccountStatus.DEACTIVATED.value:
            raise DomainException("복구할 수 없는 계정입니다.")
        account = self._repo.get_by_id(account_id)
        if account is None:
            raise DomainException("복구할 수 없는 계정입니다.")
        account.status = AccountStatus.ACTIVE.value
        self._repo.update_account(account)
        self._repo.delete_account_deletion(account_id)
        logger.info({"event": "AccountReactivated", "accountId": account_id})

    async def purge_job(self, now: datetime | None = None) -> int:
        """유예 경과 계정을 영구 파기한다(비동기 잡). 멱등 — 이미 PURGED는 제외.

        각 계정: AccountDeleted 발행(구독자 owner-scoped 파기) → 자격증명 영구 삭제 → PURGED.
        발행 실패 시 해당 계정은 다음 회차에 재시도된다(DEACTIVATED 유지·at-least-once).
        반환: 파기한 계정 수."""
        now = now or _now()
        purged = 0
        for rec in self._repo.get_due_deletions(now):
            account_id = rec.account_id
            event_id = str(uuid.uuid4())
            # 먼저 캐스케이드 이벤트 발행(U4/U2/U11 owner-scoped 파기 — 멱등·재시도·DLQ).
            await self._publisher.publish(account_id, _now(), event_id)
            self._repo.delete_account_permanently(account_id)
            self._repo.mark_deletion_purged(account_id)
            purged += 1
            logger.info({"event": "AccountPurged", "accountId": account_id, "eventId": event_id})
        return purged
