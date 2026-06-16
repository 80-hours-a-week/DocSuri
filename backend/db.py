"""SQLAlchemy engine/session seam.

This is the concrete fill for the DI seam the accounts module (U3) declares: its
``controller.get_db_session`` raises *"must be overridden by app shell"* until the shell
binds it to a real session factory (see ``backend.wiring._mount_accounts``).

The shell owns one engine per process (built at construction, disposed on shutdown); the
modules receive short-lived sessions via the FastAPI dependency.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    """Create the process-wide engine. Lazy connect — no server contact until first use."""
    is_sqlite = database_url.startswith("sqlite")
    # check_same_thread=False: FastAPI serves a sync Session dependency across the threadpool.
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    return create_engine(
        database_url,
        future=True,
        # pool_pre_ping avoids handing out a dead connection after an idle Postgres drop;
        # harmless for SQLite. SQLite gets no pool sizing (single-file, StaticPool default).
        pool_pre_ping=not is_sqlite,
        connect_args=connect_args,
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """A sessionmaker the accounts dependency calls per-request (commit/rollback owned by
    the module's controller; the shell only opens and closes the session)."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
