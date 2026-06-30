"""Owner-scoped data purge backstop for account hard-delete.

AccountDeleted is still published for asynchronous subscribers. This adapter handles
the same-RDS tables that already exist in the deployed monolith so the purge worker
does not leave first-party user data behind while subscriber infra catches up.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OwnerScopedTable:
    table: str
    owner_column: str = "owner_id"


# Child tables first, then parent/summary rows.
OWNER_SCOPED_TABLES: tuple[OwnerScopedTable, ...] = (
    OwnerScopedTable("research_messages"),
    OwnerScopedTable("research_jobs"),
    OwnerScopedTable("novelty_messages"),
    OwnerScopedTable("novelty_progress_events"),
    OwnerScopedTable("novelty_artifacts"),
    OwnerScopedTable("novelty_notion_exports"),
    OwnerScopedTable("novelty_jobs"),
    OwnerScopedTable("saved_searches"),
    OwnerScopedTable("library_items"),
    OwnerScopedTable("search_history"),
    OwnerScopedTable("user_behavior_events"),
    OwnerScopedTable("user_interest_profiles"),
    OwnerScopedTable("personalization_settings"),
    OwnerScopedTable("mypage_subscriptions"),
    OwnerScopedTable("user_glossary", "user_id"),
)


class SqlOwnerDataPurger:
    def __init__(
        self,
        session: Session,
        tables: Iterable[OwnerScopedTable] = OWNER_SCOPED_TABLES,
    ) -> None:
        self._session = session
        self._tables = tuple(tables)

    def purge(self, account_id: str) -> None:
        bind = self._session.get_bind()
        existing = set(inspect(bind).get_table_names())
        deleted_rows = 0

        for spec in self._tables:
            if spec.table not in existing:
                continue
            result = self._session.execute(
                text(f"DELETE FROM {spec.table} WHERE {spec.owner_column} = :account_id"),
                {"account_id": account_id},
            )
            deleted_rows += int(result.rowcount or 0)

        self._session.flush()
        logger.info(
            {"event": "OwnerScopedDataPurged", "accountId": account_id, "deletedRows": deleted_rows}
        )
