"""FR-28 / BR-A10 — AccountManagementService.

Covers: password change (re-auth current, BR-A1 on new, all-session invalidation),
email change request (verification to new + M2 notice to old, enumeration-safe no-op for
in-use addresses), and email-change confirm (delayed apply, single-use token).
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.modules.accounts.models import AccountStatus, DomainException
from backend.modules.accounts.password import get_password_hasher
from backend.modules.accounts.repository.credential import Base, CredentialRepository
from backend.modules.accounts.services.account_management import AccountManagementService, _hash_token


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _active_account(repo: CredentialRepository, session, email="user@docsuri.org", pw="OldPw123!@x"):
    acct = repo.create_account(email, get_password_hasher().hash(pw))
    acct.status = AccountStatus.ACTIVE.value
    repo.update_account(acct)
    session.commit()
    return acct


def _change_token(email_client) -> str:
    # send_email_change_verification_email(new_email, token, confirm_link) — token is positional[1].
    return email_client.send_email_change_verification_email.call_args.args[1]


# ── change_password ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_change_password_success_rehashes_and_invalidates(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    old_hash = acct.password_hash
    sm = AsyncMock()
    svc = AccountManagementService(repo, sm, AsyncMock())

    await svc.change_password(acct.id, "OldPw123!@x", "BrandNewPw9!@")
    session.commit()

    assert repo.get_by_id(acct.id).password_hash != old_hash
    sm.invalidate_all_for_user.assert_awaited_once_with(acct.id)  # BR-A10 §7.1


@pytest.mark.asyncio
async def test_change_password_wrong_current_rejected(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountManagementService(repo, AsyncMock(), AsyncMock())
    with pytest.raises(DomainException):
        await svc.change_password(acct.id, "WrongPw1!@x", "BrandNewPw9!@")


@pytest.mark.asyncio
async def test_change_password_weak_new_rejected(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountManagementService(repo, AsyncMock(), AsyncMock())
    with pytest.raises(DomainException):
        await svc.change_password(acct.id, "OldPw123!@x", "weak")


# ── request_email_change ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_request_email_change_sends_verification_and_notice(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    email_client = AsyncMock()
    email_client.send_email_change_verification_email.return_value = True
    email_client.send_email_change_notice_email.return_value = True
    svc = AccountManagementService(repo, AsyncMock(), email_client)

    await svc.request_email_change(acct.id, "New@docsuri.org", "https://docsuri.org/email-change/confirm")
    session.commit()

    email_client.send_email_change_verification_email.assert_awaited_once()
    email_client.send_email_change_notice_email.assert_awaited_once()  # M2 notice to current email
    token = _change_token(email_client)
    assert repo.get_email_change_request(_hash_token(token)) is not None


@pytest.mark.asyncio
async def test_request_email_change_in_use_is_noop(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    _active_account(repo, session, email="taken@docsuri.org")
    email_client = AsyncMock()
    svc = AccountManagementService(repo, AsyncMock(), email_client)

    await svc.request_email_change(acct.id, "taken@docsuri.org", "https://x/confirm")
    email_client.send_email_change_verification_email.assert_not_awaited()  # enumeration-safe (SEC-BR-2)


@pytest.mark.asyncio
async def test_request_email_change_same_email_rejected(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountManagementService(repo, AsyncMock(), AsyncMock())
    with pytest.raises(DomainException):
        await svc.request_email_change(acct.id, "user@docsuri.org", "https://x/confirm")


# ── confirm_email_change ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_confirm_email_change_applies_and_consumes(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    email_client = AsyncMock()
    email_client.send_email_change_verification_email.return_value = True
    email_client.send_email_change_notice_email.return_value = True
    svc = AccountManagementService(repo, AsyncMock(), email_client)

    await svc.request_email_change(acct.id, "new@docsuri.org", "https://x/confirm")
    session.commit()
    token = _change_token(email_client)

    await svc.confirm_email_change(token)
    session.commit()

    assert repo.get_by_id(acct.id).email == "new@docsuri.org"  # delayed apply now committed
    assert repo.get_email_change_request(_hash_token(token)) is None  # single-use consumed
    with pytest.raises(DomainException):
        await svc.confirm_email_change(token)  # reuse rejected


@pytest.mark.asyncio
async def test_confirm_email_change_invalid_token_rejected(session):
    repo = CredentialRepository(session)
    svc = AccountManagementService(repo, AsyncMock(), AsyncMock())
    with pytest.raises(DomainException):
        await svc.confirm_email_change("nonexistent-token")
