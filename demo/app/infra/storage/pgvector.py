"""Async pgvector similarity search client (infra/CLAUDE.md — storage 규칙).

Executes cosine-similarity queries against a PostgreSQL `papers` table
that has a `embedding vector(3072)` column managed by pgvector.

Query pattern (AGENTS.md §…):
    SELECT id, title, abstract,
           1 - (embedding <=> $1::vector) AS score
    FROM papers
    WHERE year >= $2          -- optional
    ORDER BY embedding <=> $1::vector
    LIMIT $3;

`asyncpg` is imported lazily so a missing package does not break startup
(the client is wired by container only when DATABASE_URL is set).

Vector dimension: 3072 (text-embedding-3-large). Switching models requires
an Alembic migration to resize the column and a full re-embedding run.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 3072  # text-embedding-3-large — must match pgvector column DDL

# ── SQL ──────────────────────────────────────────────────────────────────────
_SQL_SEARCH = """
    SELECT id, title, abstract,
           1 - (embedding <=> ($1)::vector) AS score
    FROM papers
    WHERE ($2::int IS NULL OR year >= $2)
    ORDER BY embedding <=> ($1)::vector
    LIMIT $3
"""


@dataclass
class VectorSearchResult:
    """One row returned by a pgvector similarity search."""

    paper_id: str       # papers.id — same namespace as PaperSummary.id
    title: str
    abstract: str
    score: float        # cosine similarity ∈ [0, 1]; higher = more similar


def _vec_str(vector: list[float]) -> str:
    """Serialise a float list to pgvector text literal: [v0,v1,...,vN-1]."""
    return "[" + ",".join(str(v) for v in vector) + "]"


class PgVectorClient:
    """Async pgvector similarity search client backed by an asyncpg pool.

    Caller owns lifecycle — call `aclose()` during application shutdown
    (e.g. FastAPI lifespan) to drain the connection pool gracefully.

    The pool is created lazily on the first `search()` call so that the
    container can construct the client without an immediate DB connection.
    """

    def __init__(
        self,
        dsn: str | None = None,
        *,
        min_pool_size: int = 1,
        max_pool_size: int = 5,
    ) -> None:
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._min_pool = min_pool_size
        self._max_pool = max_pool_size
        self._pool = None  # lazy

    async def _ensure_pool(self) -> object:
        if self._pool is not None:
            return self._pool
        try:
            import asyncpg  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "asyncpg not installed; add `asyncpg` to project dependencies."
            ) from exc
        if not self._dsn:
            raise RuntimeError("DATABASE_URL is not set; cannot create pgvector pool.")
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._min_pool,
            max_size=self._max_pool,
        )
        return self._pool

    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        year_from: int | None = None,
    ) -> list[VectorSearchResult]:
        """Find the `limit` papers closest to `query_vector` by cosine similarity.

        Args:
            query_vector: Embedding of the search query (must be EMBEDDING_DIM floats).
            limit:        Maximum number of results to return.
            year_from:    Optional lower-bound filter on `papers.year` (inclusive).
        """
        if len(query_vector) != EMBEDDING_DIM:
            raise ValueError(
                f"query_vector has {len(query_vector)} dims; expected {EMBEDDING_DIM}"
            )

        pool = await self._ensure_pool()
        vec = _vec_str(query_vector)

        logger.info(
            "pgvector.search limit=%d year_from=%s", limit, year_from
        )

        async with pool.acquire() as conn:  # type: ignore[attr-defined]
            rows = await conn.fetch(_SQL_SEARCH, vec, year_from, limit)

        return [
            VectorSearchResult(
                paper_id=row["id"],
                title=row["title"] or "",
                abstract=row["abstract"] or "",
                score=float(row["score"]),
            )
            for row in rows
        ]

    async def has_paper(self, paper_id: str) -> bool:
        """Return True if a row for `paper_id` already exists (idempotency gate)."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(
                "SELECT 1 FROM papers WHERE id = $1", paper_id
            )
        return row is not None

    async def upsert_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        year: int | None,
        vector: list[float],
        *,
        doi: str | None = None,
    ) -> None:
        """Insert or update paper + embedding.

        When `doi` is provided and a row with the same DOI already exists,
        updates title and updated_at only if the existing row is older —
        preventing stale data from overwriting a newer record.
        The column DDL must be `embedding vector(3072)` — enforced by Alembic
        migration. Mismatched dimensions raise ValueError before touching the DB.
        """
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(
                f"vector has {len(vector)} dims; expected {EMBEDDING_DIM}"
            )
        pool = await self._ensure_pool()
        vec = _vec_str(vector)
        async with pool.acquire() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                """
                INSERT INTO papers (id, doi, title, abstract, year, embedding, updated_at)
                VALUES ($1, $2, $3, $4, $5, ($6)::vector, NOW())
                ON CONFLICT (doi) DO UPDATE SET
                    title = EXCLUDED.title,
                    updated_at = NOW()
                WHERE papers.updated_at < EXCLUDED.updated_at
                """,
                paper_id,
                doi,
                title,
                abstract,
                year,
                vec,
            )
        logger.info("pgvector.upsert paper_id=%s", paper_id)

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.close()  # type: ignore[attr-defined]
            self._pool = None
