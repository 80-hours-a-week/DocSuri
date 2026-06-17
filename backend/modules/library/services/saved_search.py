"""U4 — SavedSearchService (US-L1/FR-8): save, list, delete, rerun a user's queries."""

from __future__ import annotations

from uuid import uuid4

from backend.modules.accounts.models import Action, Principal

from ..audit import make_event
from ..authz import authorize_owned
from ..models import NotFoundError, QuotaExceededError, SavedSearch
from ..ports import AuditSink, SearchGatewayPort, UserDataRepository
from ..schemas import (
    SavedSearchCreateDTO,
    SavedSearchDTO,
    SavedSearchPageDTO,
    SearchResultSetDTO,
)
from ..validation import (
    build_page,
    normalize_query,
    to_saved_dto,
    validate_label,
    validate_query,
)

MAX_SAVED_PER_OWNER = 200  # BR-L2


class SavedSearchService:
    def __init__(
        self, repo: UserDataRepository, gateway: SearchGatewayPort, audit: AuditSink
    ) -> None:
        self._repo = repo
        self._gateway = gateway
        self._audit = audit

    def save(self, principal: Principal, dto: SavedSearchCreateDTO) -> SavedSearchDTO:
        query = validate_query(dto.query)
        label = validate_label(dto.label)
        normalized = normalize_query(query)
        owner = principal.user_id
        repo = self._repo.saved_searches

        # BR-L1: idempotent on (owner, normalized_query) — re-save returns existing, may relabel.
        existing = repo.find_by_normalized(owner, normalized)
        if existing is not None:
            if label is not None and label != existing.label:
                repo.update_label(owner, existing.id, label)
            return to_saved_dto(existing)

        # BR-L2: per-owner quota.
        if repo.count(owner) >= MAX_SAVED_PER_OWNER:
            raise QuotaExceededError(
                f"saved-search limit of {MAX_SAVED_PER_OWNER} reached"
            )

        entity = SavedSearch(
            id=str(uuid4()),
            owner_id=owner,
            query=query,
            normalized_query=normalized,
            label=label,
        )
        repo.insert(entity)
        self._audit.record(make_event("saved_search.create", "saved_search", entity.id, owner))
        return to_saved_dto(entity)

    def list(self, principal: Principal, params) -> SavedSearchPageDTO:
        return build_page(
            self._repo.saved_searches.list_page,
            principal.user_id,
            params,
            key_of=lambda s: (s.created_at, s.id),
            to_dto=to_saved_dto,
            page_ctor=SavedSearchPageDTO,
        )

    def delete(self, principal: Principal, item_id: str) -> None:
        entity = self._repo.saved_searches.get(principal.user_id, item_id)
        if entity is None:
            raise NotFoundError("saved search not found")  # SEC-9 generalized
        authorize_owned(principal, Action.DELETE, entity.owner_id)  # SEC-8 single authority
        self._repo.saved_searches.delete(principal.user_id, item_id)
        self._audit.record(
            make_event("saved_search.delete", "saved_search", item_id, principal.user_id)
        )

    async def rerun(self, principal: Principal, item_id: str) -> SearchResultSetDTO:
        entity = self._repo.saved_searches.get(principal.user_id, item_id)
        if entity is None:
            raise NotFoundError("saved search not found")
        authorize_owned(principal, Action.RERUN, entity.owner_id)
        # INV-L2: re-enter the gateway-fronted search contract (never a direct U2 call).
        return await self._gateway.search(entity.query, principal)
