"""
Async SQLAlchemy engine + session factory.

Uses a per-event-loop cache so that in tests (where each test may get its own
event loop) the engine is created fresh per loop — no cross-loop connection reuse.
In production (`uvicorn`) there's only one loop, so the cache yields the same engine.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()

# loop -> (engine, sessionmaker)
_cache: dict[asyncio.AbstractEventLoop, tuple[AsyncEngine, async_sessionmaker[AsyncSession]]] = {}


def _get_engine_and_factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    loop = asyncio.get_running_loop()
    cached = _cache.get(loop)
    if cached is not None:
        return cached
    engine = create_async_engine(
        _settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    _cache[loop] = (engine, factory)
    return engine, factory


# Convenience proxy objects — behave like the old `engine` and `AsyncSessionLocal`
# by forwarding to the per-loop cached instances.
class _EngineProxy:
    def __getattr__(self, name):
        return getattr(_get_engine_and_factory()[0], name)


class _SessionFactoryProxy:
    def __call__(self, *args, **kwargs):
        return _get_engine_and_factory()[1](*args, **kwargs)


engine = _EngineProxy()
AsyncSessionLocal = _SessionFactoryProxy()


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields an AsyncSession, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
