"""Idempotent admin seeding (BR-A7).

ADMIN accounts are NEVER created via public signup (privilege-escalation guard) — they are
provisioned only here. Run once per environment:

    DOCSURI_ADMIN_EMAIL=admin@docsuri.dev DOCSURI_ADMIN_PASSWORD='…' \\
        DATABASE_URL=postgresql+psycopg://… python -m backend.modules.accounts.seed_admin

Idempotent: an existing account with that email is promoted to ADMIN/ACTIVE (not duplicated);
its password is NOT overwritten. The admin enrolls TOTP MFA on first login (/auth/mfa/enroll)
before the admin control plane unlocks. The plaintext password is read from env once and is
never logged (SEC-3)."""

from __future__ import annotations

import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import AccountStatus, UserRole
from .password import PasswordPolicy, get_password_hasher
from .repository.credential import AccountTable, Base, CredentialRepository

logger = logging.getLogger(__name__)


def seed_admin(db_session, email: str, password: str) -> str:
    """Idempotent: 주어진 이메일의 계정을 ADMIN·ACTIVE로 보장하고 그 id를 반환한다.
    신규면 강도 정책 검증 후 해싱하여 생성하고, 기존이면 ADMIN·ACTIVE로 승격한다(비번 미변경)."""
    repo = CredentialRepository(db_session)
    account = repo.get_by_email(email)
    if account is None:
        PasswordPolicy.evaluate(password)  # 시드 관리자도 동일 강도 정책 (BR-A1)
        account = AccountTable(
            email=email,
            password_hash=get_password_hasher().hash(password),
            status=AccountStatus.ACTIVE.value,
            role=UserRole.ADMIN.value,
        )
        db_session.add(account)
        db_session.flush()
        logger.info("Seeded new ADMIN account.")
    else:
        # 멱등: 기존 계정을 ADMIN·ACTIVE로 승격(이미 그렇다면 무변경). 비밀번호는 덮어쓰지 않는다.
        account.role = UserRole.ADMIN.value
        account.status = AccountStatus.ACTIVE.value
        repo.update_account(account)
        logger.info("Promoted existing account to ADMIN/ACTIVE.")
    db_session.commit()
    return account.id


def main() -> int:
    email = os.getenv("DOCSURI_ADMIN_EMAIL", "").strip()
    password = os.getenv("DOCSURI_ADMIN_PASSWORD", "")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not email or not password or not database_url:
        logger.error("DOCSURI_ADMIN_EMAIL · DOCSURI_ADMIN_PASSWORD · DATABASE_URL 환경변수가 모두 필요합니다.")
        return 2
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)  # 테이블 부재 시 생성(로컬/초기). 프로덕션은 마이그레이션 선행.
    session = sessionmaker(bind=engine)()
    try:
        account_id = seed_admin(session, email, password)
        logger.info("Admin seeding complete: %s", account_id)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
