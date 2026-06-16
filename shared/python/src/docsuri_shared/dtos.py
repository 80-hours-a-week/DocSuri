"""API↔client DTOs (dtos.md). Generated from ``shared/dtos/*.schema.json``.

Re-exported here under their canonical contract names so consumers import
``docsuri_shared.dtos`` and never reach into ``_generated`` (which is codegen-owned).

Producers: U2 (search), U3 (accounts), U4 (library). Consumer: U5.
SEC-9/SEC-8/SEC-12 invariants (no internal fields, no owner userId in bodies,
password input-only) are enforced by the schemas (``additionalProperties: false`` ⇒
pydantic ``extra='forbid'``) and checked by ``tests/test_security_invariants.py``.
"""

from __future__ import annotations

# U3 — Accounts/Auth (accounts.schema.json)
from ._generated.dtos.accounts_schema import (
    LoginRequest,
    SessionInfo,
    SignupRequest,
    SignupResult,
)

# U4 — Saved searches / Library / History (library.schema.json)
from ._generated.dtos.library_schema import (
    HistoryEntry,
    HistoryPageDTO,
    LibraryItemCreateDTO,
    LibraryItemDTO,
    LibraryPageDTO,
    PageParams,
    SavedSearchCreateDTO,
    SavedSearchDTO,
    SavedSearchPageDTO,
    SearchResultSetDTO,
)

# U2 — Discovery/Search (search.schema.json)
from ._generated.dtos.search_schema import (
    AbstainDTO,
    DegradationMode,
    DegradedResultDTO,
    ResultCardVM,
    ResultMeta,
    SearchRequest,
    SearchResponse,
    SearchResultPageDTO,
    ValidationErrorDTO,
)

__all__ = [
    # search
    "SearchRequest",
    "SearchResponse",
    "SearchResultPageDTO",
    "AbstainDTO",
    "DegradedResultDTO",
    "ValidationErrorDTO",
    "ResultCardVM",
    "ResultMeta",
    "DegradationMode",
    # accounts
    "SignupRequest",
    "SignupResult",
    "LoginRequest",
    "SessionInfo",
    # library
    "PageParams",
    "SavedSearchCreateDTO",
    "SavedSearchDTO",
    "SavedSearchPageDTO",
    "LibraryItemCreateDTO",
    "LibraryItemDTO",
    "LibraryPageDTO",
    "HistoryEntry",
    "HistoryPageDTO",
    "SearchResultSetDTO",
]
