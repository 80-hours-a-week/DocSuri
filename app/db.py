import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from app.config import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_pool(settings: Settings) -> AsyncIterator[asyncpg.Pool | None]:
    if not settings.database_url:
        yield None
        return

    try:
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    except Exception:
        logger.exception("PostgreSQL connection failed; falling back to demo repository.")
        yield None
        return

    try:
        yield pool
    finally:
        await pool.close()
