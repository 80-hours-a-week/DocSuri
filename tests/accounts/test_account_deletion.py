"""FR-28 / BR-A11 — AccountDeletionService (soft-delete + grace purge + AccountDeleted).

Covers: soft delete (DEACTIVATED + all-session invalidation, NO event yet — H2), grace
purge job (publishes AccountDeleted, permanently deletes credentials + cascade artifacts,
idempotent), not-yet-due skip, and reactivation within grace (M1).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.modules.accounts.models import AccountStatus, DomainException
from backend.modules.accounts.password import get_password_hasher
from backend.modules.accounts.repository.credential import Base, CredentialRepository
from backend.modules.accounts.services.account_deletion import AccountDeletionService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _naive(days=0):
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days)


def _active_account(repo: CredentialRepository, session, email="user@docsuri.org"):
    acct = repo.create_account(email, get_password_hasher().hash("OldPw123!@x"))
    acct.status = AccountStatus.ACTIVE.value
    repo.update_account(acct)
    session.commit()
    return acct


@pytest.mark.asyncio
async def test_request_deletion_soft_deletes_invalidates_no_event(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    sm = AsyncMock()
    publisher = AsyncMock()
    svc = AccountDeletionService(repo, sm, publisher)

    await svc.request_deletion(acct.id)
    session.commit()

    assert repo.get_by_id(acct.id).status == AccountStatus.DEACTIVATED.value
    assert repo.get_account_deletion(acct.id) is not None
    sm.invalidate_all_for_user.assert_awaited_once_with(acct.id)  # immediate login block
    publisher.publish.assert_not_awaited()  # H2: AccountDeleted only at purge, not soft-delete


@pytest.mark.asyncio
async def test_purge_job_publishes_event_and_permanently_deletes(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    publisher = AsyncMock()
    svc = AccountDeletionService(repo, AsyncMock(), publisher, grace_days=30)
    await svc.request_deletion(acct.id)
    session.commit()

    purged = await svc.purge_job(now=_naive(days=31))
    session.commit()

    assert purged == 1
    publisher.publish.assert_awaited_once()
    assert publisher.publish.call_args.args[0] == acct.id  # accountId is the idempotency key
    assert repo.get_by_id(acct.id) is None  # credentials permanently deleted
    assert repo.get_account_deletion(acct.id).state == "PURGED"

    # idempotent: re-running does not re-publish or re-process (PURGED excluded)
    again = await svc.purge_job(now=_naive(days=31))
    assert again == 0
    assert publisher.publish.await_count == 1


@pytest.mark.asyncio
async def test_purge_job_cascades_credential_artifacts(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    repo.create_social_identity("GOOGLE", "sub-1", acct.id, acct.email)
    repo.create_reset_token(acct.email, "resethash1", _naive(days=0) + timedelta(minutes=30))
    session.commit()
    svc = AccountDeletionService(repo, AsyncMock(), AsyncMock(), grace_days=0)
    await svc.request_deletion(acct.id)
    session.commit()

    await svc.purge_job(now=_naive(days=1))
    session.commit()

    assert repo.get_social_identity("GOOGLE", "sub-1") is None
    assert repo.get_reset_token("resethash1") is None


@pytest.mark.asyncio
async def test_purge_job_skips_not_yet_due(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountDeletionService(repo, AsyncMock(), AsyncMock(), grace_days=30)
    await svc.request_deletion(acct.id)
    session.commit()

    purged = await svc.purge_job()  # now ~= request time; purge_after = +30d → not due
    assert purged == 0
    assert repo.get_by_id(acct.id) is not None


@pytest.mark.asyncio
async def test_reactivate_restores_within_grace(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountDeletionService(repo, AsyncMock(), AsyncMock())
    await svc.request_deletion(acct.id)
    session.commit()

    await svc.reactivate(acct.id)
    session.commit()

    assert repo.get_by_id(acct.id).status == AccountStatus.ACTIVE.value
    assert repo.get_account_deletion(acct.id) is None


@pytest.mark.asyncio
async def test_reactivate_non_deleted_rejected(session):
    repo = CredentialRepository(session)
    acct = _active_account(repo, session)
    svc = AccountDeletionService(repo, AsyncMock(), AsyncMock())
    with pytest.raises(DomainException):
        await svc.reactivate(acct.id)
