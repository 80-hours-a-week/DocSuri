"""U4 — LibraryService (US-L2/FR-9): add (idempotent), list, remove personal-library papers."""

from __future__ import annotations

from uuid import uuid4

from backend.modules.accounts.models import Action, Principal

from ..audit import make_event
from ..authz import authorize_owned
from ..models import LibraryItem, NotFoundError, QuotaExceededError
from ..ports import AuditSink, UserDataRepository
from ..schemas import LibraryItemCreateDTO, LibraryItemDTO, LibraryPageDTO
from ..validation import build_page, to_library_dto, validate_arxiv_id, validate_meta

MAX_LIBRARY_PER_OWNER = 1000  # BR-L4


class LibraryService:
    def __init__(self, repo: UserDataRepository, audit: AuditSink) -> None:
        self._repo = repo
        self._audit = audit

    def add(self, principal: Principal, dto: LibraryItemCreateDTO) -> LibraryItemDTO:
        arxiv_id = validate_arxiv_id(dto.arXivId)
        meta = validate_meta(dto.meta)  # BR-L5: validated snapshot (availability isolation)
        owner = principal.user_id
        repo = self._repo.library

        # BR-L3/QT-4: idempotent on (owner, arxiv_id) — re-add returns existing, meta unchanged.
        existing = repo.find_by_arxiv(owner, arxiv_id)
        if existing is not None:
            return to_library_dto(existing)

        # BR-L4: per-owner quota.
        if repo.count(owner) >= MAX_LIBRARY_PER_OWNER:
            raise QuotaExceededError(
                f"library limit of {MAX_LIBRARY_PER_OWNER} reached"
            )

        entity = LibraryItem(id=str(uuid4()), owner_id=owner, arxiv_id=arxiv_id, meta=meta)
        repo.insert(entity)
        self._audit.record(make_event("library.add", "library_item", entity.id, owner))
        return to_library_dto(entity)

    def list(self, principal: Principal, params) -> LibraryPageDTO:
        return build_page(
            self._repo.library.list_page,
            principal.user_id,
            params,
            key_of=lambda li: (li.added_at, li.id),
            to_dto=to_library_dto,
            page_ctor=LibraryPageDTO,
        )

    def remove(self, principal: Principal, item_id: str) -> None:
        entity = self._repo.library.get(principal.user_id, item_id)
        if entity is None:
            raise NotFoundError("library item not found")  # SEC-9 generalized
        authorize_owned(principal, Action.DELETE, entity.owner_id)  # SEC-8 single authority
        self._repo.library.delete(principal.user_id, item_id)
        self._audit.record(
            make_event("library.remove", "library_item", item_id, principal.user_id)
        )
