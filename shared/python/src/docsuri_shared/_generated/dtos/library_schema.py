# DO NOT EDIT. Generated from the JSON Schema SSOT in shared/ by tools/generate.py.
# Change the schema and regenerate (§5-B); never hand-edit.

from __future__ import annotations

from typing import Any
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel
from . import search_schema


class U4SavedSearchesLibraryDtos(RootModel[Any]):
    root: Any = Field(
        ...,
        description="🟡 PROVISIONAL (refined in U4 FD). U4 Saved Searches / Library / Search History DTO contract (dtos.md §3). Producer: U4 (SavedSearchController, LibraryController, SearchHistoryController). Consumer: U5. All collection responses paginate via PageParams{limit, cursor}. INVARIANT (SEC-8/SEC-9): DTOs do NOT carry the owner `userId` externally — ownership is enforced server-side (U3.AuthorizationGuard single decision point; UserDataRepository owner-scoping is a data backstop); access to others' resources is generalized to NotFound (existence not disclosed). Internal scores/audit meta NOT exposed (SEC-9). rerun note: SearchResultSetDTO is a gateway-fronted search result (U6 ApiGatewayMiddleware -> U2), reusing the §1 search card shape (NOT a direct U2 call). All DTOs defined in $defs for per-track type generation. Trace: FR-8, FR-9, FR-10, US-L1, US-L2, US-L3, SEC-8, SEC-9.",
        title='U4 Saved Searches & Library DTOs',
    )


class PageParams(BaseModel):
    """
    Cursor-based pagination input common to all collection queries. Source: component-methods U4. Trace: dtos.md §3, FR-8, FR-9, FR-10.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    limit: int = Field(
        ...,
        description='Page size (>= 1; a page of 0 or fewer is meaningless). The upper bound (max page size) is set in U4 FD. Trace: FR-8, FR-9, FR-10.',
        ge=1,
    )
    cursor: str | None = Field(
        None,
        description="Optional. Opaque pagination cursor (continuation token); ABSENT on the first-page request and supplied from the previous page's nextCursor (symmetric with the optional nextCursor in the page DTOs). Exact semantics refined in U4 FD. Trace: FR-8, FR-9, FR-10.",
    )


class SavedSearchCreateDTO(BaseModel):
    """
    New saved-search input. owner is server-determined from the session context (NOT in the body, SEC-8). Trace: dtos.md §3, FR-8, US-L1.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    query: str = Field(..., description='Search query to save. Trace: FR-8, US-L1.')
    label: str | None = Field(
        None,
        description='Optional user label for the saved search. Trace: FR-8, US-L1.',
    )


class SavedSearchDTO(BaseModel):
    """
    Single saved search (owner userId NOT exposed, SEC-9). Trace: dtos.md §3, FR-8, US-L1, SEC-9.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    id: Any = Field(..., description='Saved-search identifier. Trace: FR-8, US-L1.')
    query: str = Field(..., description='Saved query string. Trace: FR-8, US-L1.')
    label: str | None = Field(
        None, description='Optional user label. Trace: FR-8, US-L1.'
    )
    createdAt: AwareDatetime = Field(
        ...,
        description='Creation instant (serialized as RFC 3339 / ISO 8601 date-time — concrete wire format is API/Infra Design). Trace: FR-8, US-L1.',
    )


class SavedSearchPageDTO(BaseModel):
    """
    Page of the user's saved searches, most-recent first (owner-scoped server-side). Trace: dtos.md §3, FR-8, US-L1.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    items: list[SavedSearchDTO] = Field(
        ..., description='Saved searches in this page. Trace: FR-8, US-L1.'
    )
    nextCursor: str | None = Field(
        None,
        description='Optional. Continuation cursor for the next page (absent on the last page). Trace: FR-8, US-L1.',
    )


class LibraryItemCreateDTO(BaseModel):
    """
    Idempotent library-add input. (userId, arXivId) is idempotent server-side. Meta snapshot is preserved (NOT dependent on U2/index availability). owner NOT in the body (SEC-8). Trace: dtos.md §3, FR-9, US-L2.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    arXivId: str = Field(
        ...,
        description='arXiv ID of the paper to add (field name per dtos.md §3; display arXiv ID, may include version). Trace: FR-9, US-L2.',
    )
    meta: Any = Field(
        ...,
        description='Metadata snapshot captured at add time (preserved independent of the live index, availability isolation). Shape refined in U4 FD. Trace: FR-9, US-L2.',
    )


class LibraryItemDTO(BaseModel):
    """
    Single library item (owner userId NOT exposed, SEC-9). Idempotent add returns the same shape whether new or existing. Trace: dtos.md §3, FR-9, US-L2, SEC-9.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    id: Any = Field(..., description='Library-item identifier. Trace: FR-9, US-L2.')
    arXivId: str = Field(
        ...,
        description='arXiv ID (field name per dtos.md §3; display arXiv ID, may include version). Trace: FR-9, US-L2.',
    )
    meta: Any = Field(
        ...,
        description='Preserved metadata snapshot (returned as captured; availability isolation). Shape refined in U4 FD. Trace: FR-9, US-L2.',
    )
    addedAt: AwareDatetime = Field(
        ...,
        description='Add instant (serialized as RFC 3339 / ISO 8601 date-time — concrete wire format is API/Infra Design). Trace: FR-9, US-L2.',
    )


class LibraryPageDTO(BaseModel):
    """
    Page of the user's library (owner-scoped server-side). Returns preserved meta snapshots only (availability isolation). Trace: dtos.md §3, FR-9, US-L2.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    items: list[LibraryItemDTO] = Field(
        ..., description='Library items in this page. Trace: FR-9, US-L2.'
    )
    nextCursor: str | None = Field(
        None,
        description='Optional. Continuation cursor for the next page (absent on the last page). Trace: FR-9, US-L2.',
    )


class HistoryEntry(BaseModel):
    """
    Single search-history entry (source: SearchExecutedEvent async record; owner userId NOT exposed, SEC-9). Trace: dtos.md §3, FR-10, US-L3, SEC-9.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    id: Any = Field(..., description='History-entry identifier. Trace: FR-10, US-L3.')
    query: str = Field(..., description='Executed query string. Trace: FR-10, US-L3.')
    executedAt: AwareDatetime = Field(
        ...,
        description='Search execution instant (serialized as RFC 3339 / ISO 8601 date-time — concrete wire format is API/Infra Design). Source maps to SearchExecutedEvent.timestamp. Trace: FR-10, US-L3.',
    )
    resultCount: int = Field(
        ...,
        description='Number of results returned for this search (int). Source maps to SearchExecutedEvent.resultCount. Trace: FR-10, US-L3.',
    )


class HistoryPageDTO(BaseModel):
    """
    Page of recent search history, most-recent first (owner-scoped server-side). Trace: dtos.md §3, FR-10, US-L3.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    items: list[HistoryEntry] = Field(
        ..., description='History entries in this page. Trace: FR-10, US-L3.'
    )
    nextCursor: str | None = Field(
        None,
        description='Optional. Continuation cursor for the next page (absent on the last page). Trace: FR-10, US-L3.',
    )


class SearchResultSetDTO(RootModel[search_schema.SearchResultPageDTO]):
    root: search_schema.SearchResultPageDTO = Field(
        ...,
        description='Saved-search / history RERUN result. Surfaces a gateway-fronted search (U6.ApiGatewayMiddleware -> U2) as the §1 search card DTO — REUSES the SearchResultPageDTO shape from search.schema.json (NOT a direct U2 call). Trace: dtos.md §3, FR-8, FR-10, US-L1, US-L3.',
        title='SearchResultSetDTO',
    )
