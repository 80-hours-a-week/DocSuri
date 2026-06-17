"""U4 — keyset cursor pagination (BR-L8): completeness, order, opacity, tamper rejection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.library.models import SavedSearch, ValidationException
from backend.modules.library.repository.memory import InMemoryUserDataRepository
from backend.modules.library.schemas import PageParams
from backend.modules.library.services.saved_search import SavedSearchService
from backend.modules.library.gateway import StubSearchGateway
from backend.modules.library.audit import InMemoryAuditSink
from backend.modules.library.validation import decode_cursor, encode_cursor


def _seed(repo: InMemoryUserDataRepository, owner_id: str, n: int) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(n):
        repo.saved_searches.insert(
            SavedSearch(
                id=str(uuid.uuid4()),
                owner_id=owner_id,
                query=f"q{i}",
                normalized_query=f"q{i}",
                created_at=base + timedelta(seconds=i),
            )
        )


def test_pagination_covers_all_items_once_in_order(make_principal):
    repo = InMemoryUserDataRepository()
    svc = SavedSearchService(repo, StubSearchGateway(), InMemoryAuditSink())
    p = make_principal()
    _seed(repo, p.user_id, 23)

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        page = svc.list(p, PageParams(limit=5, cursor=cursor))
        seen.extend(it.query for it in page.items)
        pages += 1
        cursor = page.nextCursor
        if cursor is None:
            break
        assert pages < 100  # guard against an infinite loop

    assert len(seen) == 23
    assert len(set(seen)) == 23  # no duplicates, no gaps
    # most-recent-first: q22, q21, ... q0
    assert seen == [f"q{i}" for i in range(22, -1, -1)]


def test_last_page_has_no_next_cursor(make_principal):
    repo = InMemoryUserDataRepository()
    svc = SavedSearchService(repo, StubSearchGateway(), InMemoryAuditSink())
    p = make_principal()
    _seed(repo, p.user_id, 3)
    page = svc.list(p, PageParams(limit=10))
    assert len(page.items) == 3
    assert page.nextCursor is None


def test_limit_over_max_rejected(make_principal):
    repo = InMemoryUserDataRepository()
    svc = SavedSearchService(repo, StubSearchGateway(), InMemoryAuditSink())
    p = make_principal()
    with pytest.raises(ValidationException):
        svc.list(p, PageParams(limit=101))


def test_tampered_cursor_rejected(make_principal):
    repo = InMemoryUserDataRepository()
    svc = SavedSearchService(repo, StubSearchGateway(), InMemoryAuditSink())
    p = make_principal()
    with pytest.raises(ValidationException):
        svc.list(p, PageParams(limit=5, cursor="!!!not-base64!!!"))


def test_cursor_codec_roundtrip():
    key = (datetime(2026, 6, 17, 12, 0, tzinfo=UTC), "abc-123")
    assert decode_cursor(encode_cursor(key)) == key
    assert decode_cursor(None) is None
