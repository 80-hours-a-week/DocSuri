from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from app.config import Settings


@asynccontextmanager
async def create_pool(settings: Settings) -> AsyncIterator[asyncpg.Pool]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required.")

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    try:
        yield pool
    finally:
        await pool.close()
