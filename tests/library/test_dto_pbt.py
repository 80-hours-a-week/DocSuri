"""U4 — PBT-09 DTO round-trip + SEC-9 non-disclosure properties (Hypothesis).

Property: mapping any valid domain entity to its wire DTO (1) never raises, (2) preserves the
public fields, and (3) NEVER leaks an internal field (owner_id / normalized_query / dedupe_key).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from backend.modules.library.models import HistoryEntry, LibraryItem, SavedSearch
from backend.modules.library.schemas import LibraryItemMeta
from backend.modules.library.validation import to_history_dto, to_library_dto, to_saved_dto

# internal fields that MUST NEVER appear on the wire (SEC-9)
FORBIDDEN = {"owner_id", "normalized_query", "dedupe_key", "ownerId"}

_aware = st.datetimes(
    min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
).map(lambda d: d.replace(tzinfo=UTC))
_text = st.text(min_size=1, max_size=200)
_uuid = st.builds(lambda: str(uuid.uuid4()))


@given(query=_text, label=st.none() | _text, created=_aware, owner=_uuid)
def test_saved_search_dto_roundtrip(query, label, created, owner):
    entity = SavedSearch(
        id=str(uuid.uuid4()),
        owner_id=owner,
        query=query,
        normalized_query=query.casefold(),
        created_at=created,
        label=label,
    )
    dto = to_saved_dto(entity)
    assert dto.query == entity.query
    assert dto.label == entity.label
    assert dto.createdAt == entity.created_at
    dumped = dto.model_dump()
    assert FORBIDDEN.isdisjoint(dumped.keys())
    # serialize → re-validate is stable
    assert type(dto).model_validate(dumped).id == dto.id


@given(
    title=st.text(min_size=1, max_size=200),
    authors=st.lists(st.text(min_size=1, max_size=50), max_size=5),
    year=st.none() | st.integers(min_value=1900, max_value=2100),
    added=_aware,
    owner=_uuid,
)
def test_library_item_dto_roundtrip(title, authors, year, added, owner):
    meta = LibraryItemMeta(title=title, authors=authors, year=year, arxivId="2401.00001")
    entity = LibraryItem(
        id=str(uuid.uuid4()), owner_id=owner, arxiv_id="2401.00001", meta=meta, added_at=added
    )
    dto = to_library_dto(entity)
    assert dto.arXivId == "2401.00001"
    assert dto.meta["title"] == title
    dumped = dto.model_dump()
    assert FORBIDDEN.isdisjoint(dumped.keys())


@given(query=_text, count=st.integers(min_value=0, max_value=10_000), executed=_aware, owner=_uuid)
def test_history_entry_dto_roundtrip(query, count, executed, owner):
    entity = HistoryEntry(
        id=str(uuid.uuid4()),
        owner_id=owner,
        query=query,
        executed_at=executed,
        result_count=count,
        dedupe_key="deadbeef",
    )
    dto = to_history_dto(entity)
    assert dto.query == entity.query
    assert dto.resultCount == count
    dumped = dto.model_dump()
    assert FORBIDDEN.isdisjoint(dumped.keys())
