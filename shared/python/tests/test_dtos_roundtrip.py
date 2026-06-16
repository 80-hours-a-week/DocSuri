"""DTO models round-trip and enforce additionalProperties:false (extra='forbid')."""

from __future__ import annotations

import pytest
from conftest import valid_card_dict
from pydantic import ValidationError

from docsuri_shared import dtos


def test_result_card_roundtrip():
    card = dtos.ResultCardVM.model_validate(valid_card_dict())
    assert card.model_dump() == valid_card_dict()


def test_search_result_page_roundtrip():
    payload = {"cards": [valid_card_dict()], "meta": {"resultCount": 1, "degraded": False}}
    page = dtos.SearchResultPageDTO.model_validate(payload)
    assert page.model_dump(exclude_none=True) == payload
    assert page.cards[0].title == "Attention Is All You Need"


def test_card_rejects_extra_field():
    # SEC-9: internal fields (vector, chunkId, ...) must never ride on a card.
    with pytest.raises(ValidationError):
        dtos.ResultCardVM.model_validate({**valid_card_dict(), "vector": [0.1, 0.2]})


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {"cards": [valid_card_dict()], "meta": {"resultCount": 1, "degraded": False}},
            "SearchResultPageDTO",
        ),
        ({"reason": "out-of-corpus"}, "AbstainDTO"),
        ({"field": "query", "message": "Query must not be empty."}, "ValidationErrorDTO"),
        (
            {
                "cards": [valid_card_dict()],
                "meta": {"resultCount": 1, "degraded": True, "degradationMode": "lexical-only"},
                "mode": "lexical-only",
            },
            "DegradedResultDTO",
        ),
    ],
)
def test_search_response_union_dispatch(payload, expected):
    resp = dtos.SearchResponse.model_validate(payload)
    assert type(resp.root).__name__ == expected


def test_search_request_validation():
    assert dtos.SearchRequest.model_validate({"query": "transformers"}).query == "transformers"
    # FR-1/SEC-5: empty query and >500 chars are rejected by the schema constraints.
    with pytest.raises(ValidationError):
        dtos.SearchRequest.model_validate({"query": ""})
    with pytest.raises(ValidationError):
        dtos.SearchRequest.model_validate({"query": "x" * 501})


def test_saved_search_and_history_optional_cursor():
    page = dtos.SavedSearchPageDTO.model_validate(
        {"items": [{"id": "s1", "query": "q", "createdAt": "2026-06-16T00:00:00Z"}]}
    )
    assert page.nextCursor is None
    hist = dtos.HistoryEntry.model_validate(
        {"id": "h1", "query": "q", "executedAt": "2026-06-16T00:00:00Z", "resultCount": 3}
    )
    assert hist.resultCount == 3


def test_search_result_set_reuses_search_page_shape():
    # rerun DTO reuses the §1 card shape via the cross-file $ref.
    payload = {"cards": [valid_card_dict()], "meta": {"resultCount": 1, "degraded": False}}
    rerun = dtos.SearchResultSetDTO.model_validate(payload)
    assert rerun.root.cards[0].arxivId == "2106.01234v1"


def test_page_params_cursor_is_optional():
    # First-page requests carry no cursor; only limit is required.
    assert dtos.PageParams.model_validate({"limit": 20}).cursor is None
    assert dtos.PageParams.model_validate({"limit": 20, "cursor": "abc"}).cursor == "abc"


def test_page_params_limit_must_be_positive():
    # A page of 0 or fewer is meaningless and must be rejected by the contract.
    for bad in (0, -5):
        with pytest.raises(ValidationError):
            dtos.PageParams.model_validate({"limit": bad})
