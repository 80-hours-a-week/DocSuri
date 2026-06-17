from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from docsuri_ingestion.domain.enums import DedupDecision, DedupStateKind
from docsuri_ingestion.domain.models import DedupResult, DedupState, IngestionJob, Watermark


class PostgresControlPlaneStore:
    """Postgres implementation of U1 control-plane state.

    The CAS statements are deliberately conditional on `current_version <= incoming`.
    This enforces BR-14 strictly-newer-vN-wins for both upserts and tombstones.
    """

    def __init__(self, dsn: str, *, min_pool_size: int = 2, max_pool_size: int = 5) -> None:
        self._dsn = dsn
        self._pool: Any = None
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size

    def _get_pool(self) -> Any:
        if self._pool is None:
            from psycopg_pool import ConnectionPool

            self._pool = ConnectionPool(
                self._dsn,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
            )
        return self._pool

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        with self._get_pool().connection() as conn:
            yield conn

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def get_watermark(self, name: str = "arxiv") -> Watermark:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT updated_at FROM watermark WHERE name = %s",
                (name,),
            ).fetchone()
        if row is None:
            return Watermark.epoch(name)
        return Watermark(name=name, updated_at=_ensure_utc(row[0]))

    def advance_watermark(self, name: str, candidate: datetime) -> Watermark:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO watermark(name, updated_at)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE
                    SET updated_at = GREATEST(watermark.updated_at, EXCLUDED.updated_at)
                RETURNING updated_at
                """,
                (name, candidate),
            ).fetchone()
            conn.commit()
        return Watermark(name=name, updated_at=_ensure_utc(row[0]))

    def reset_watermark_for_rebuild(self, name: str, value: datetime) -> Watermark:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO watermark(name, updated_at)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET updated_at = EXCLUDED.updated_at
                RETURNING updated_at
                """,
                (name, value),
            ).fetchone()
            conn.commit()
        return Watermark(name=name, updated_at=_ensure_utc(row[0]))

    def evaluate_dedup(self, paper_id: str, version: int, fingerprint: str) -> DedupResult:
        state = self._get_dedup_state(paper_id)
        if state is None:
            return DedupResult(DedupDecision.NEW)
        if version < state.current_version:
            return DedupResult(DedupDecision.STALE, state)
        if (
            version == state.current_version
            and state.fingerprint == fingerprint
            and state.state is DedupStateKind.INDEXED
        ):
            return DedupResult(DedupDecision.DUPLICATE, state)
        return DedupResult(DedupDecision.CHANGED, state)

    def try_claim_upsert(self, paper_id: str, version: int, fingerprint: str) -> bool:
        del fingerprint
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO dedup_state(paper_id, current_version, fingerprint, state)
                VALUES (%s, %s, NULL, 'INDEXED')
                ON CONFLICT (paper_id) DO UPDATE
                    SET current_version = EXCLUDED.current_version,
                        state = 'INDEXED',
                        updated_at = now()
                    WHERE dedup_state.current_version <= EXCLUDED.current_version
                RETURNING paper_id
                """,
                (paper_id, version),
            ).fetchone()
            conn.commit()
        return row is not None

    def mark_ingested(self, paper_id: str, version: int, fingerprint: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE dedup_state
                   SET fingerprint = %s,
                       state = 'INDEXED',
                       ingested_at = now(),
                       updated_at = now()
                 WHERE paper_id = %s
                   AND current_version = %s
                """,
                (fingerprint, paper_id, version),
            )
            conn.commit()

    def try_claim_tombstone(self, paper_id: str, version: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO dedup_state(paper_id, current_version, fingerprint, state)
                VALUES (%s, %s, NULL, 'TOMBSTONED')
                ON CONFLICT (paper_id) DO UPDATE
                    SET current_version = EXCLUDED.current_version,
                        fingerprint = NULL,
                        state = 'TOMBSTONED',
                        updated_at = now()
                    WHERE dedup_state.current_version <= EXCLUDED.current_version
                RETURNING paper_id
                """,
                (paper_id, version),
            ).fetchone()
            conn.commit()
        return row is not None

    def acquire_rebuild_lock(self, owner: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO rebuild_lock(lock_key, owner)
                VALUES ('REBUILD', %s)
                ON CONFLICT (lock_key) DO NOTHING
                RETURNING lock_key
                """,
                (owner,),
            ).fetchone()
            conn.commit()
        return row is not None

    def release_rebuild_lock(self, owner: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM rebuild_lock WHERE lock_key = 'REBUILD' AND owner = %s",
                (owner,),
            )
            conn.commit()

    def is_rebuild_active(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM rebuild_lock WHERE lock_key = 'REBUILD'").fetchone()
        return row is not None

    def record_job_started(self, job: IngestionJob) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_job(job_id, kind, arxiv_ref, event_id, correlation_id, status)
                VALUES (%s, %s, %s, %s, %s, 'STARTED')
                ON CONFLICT (job_id) DO UPDATE
                    SET status = 'STARTED',
                        detail = NULL,
                        started_at = now(),
                        finished_at = NULL
                """,
                (job.job_id, job.kind.value, job.arxiv_ref, job.event_id, job.correlation_id),
            )
            conn.commit()

    def record_job_finished(self, job_id: str, *, success: bool, detail: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_job
                   SET status = %s,
                       detail = %s,
                       finished_at = now()
                 WHERE job_id = %s
                """,
                ("SUCCEEDED" if success else "FAILED", detail, job_id),
            )
            conn.commit()

    def _get_dedup_state(self, paper_id: str) -> DedupState | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT paper_id, current_version, fingerprint, state, ingested_at
                  FROM dedup_state
                 WHERE paper_id = %s
                """,
                (paper_id,),
            ).fetchone()
        if row is None:
            return None
        return DedupState(
            paper_id=row[0],
            current_version=row[1],
            fingerprint=row[2],
            state=DedupStateKind(row[3]),
            ingested_at=_ensure_utc(row[4]) if row[4] else None,
        )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
