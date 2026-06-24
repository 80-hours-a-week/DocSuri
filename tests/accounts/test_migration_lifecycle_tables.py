"""003 migration ↔ SQLAlchemy model parity for the FR-26/27/28 lifecycle tables.

Guards against the migration DDL drifting from the ORM models (a forgotten/renamed
column would let the app start then 500 at runtime). Runs the DDL on stdlib in-memory
SQLite (no new deps; 003 is pure CREATE TABLE/INDEX IF NOT EXISTS — SQLite-compatible).
"""

import sqlite3
from pathlib import Path

import pytest

from backend.modules.accounts.repository.credential import (
    AccountDeletionTable,
    EmailChangeRequestTable,
    PasswordResetTokenTable,
    SocialIdentityTable,
)

MIGRATION = Path("backend/modules/accounts/migrations/003_create_lifecycle_tables.sql")


@pytest.mark.parametrize(
    "model",
    [PasswordResetTokenTable, SocialIdentityTable, EmailChangeRequestTable, AccountDeletionTable],
)
def test_migration_columns_cover_model(model):
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(MIGRATION.read_text(encoding="utf-8"))
        created = {row[1] for row in conn.execute(f"PRAGMA table_info({model.__tablename__})")}
    finally:
        conn.close()
    expected = {c.name for c in model.__table__.columns}
    assert created, f"migration did not create table {model.__tablename__}"
    assert expected <= created, f"{model.__tablename__}: model columns missing from DDL: {expected - created}"
