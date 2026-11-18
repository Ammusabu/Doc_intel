"""Idempotent DB bootstrap: enable pgvector, create tables & indexes."""
import asyncio

from sqlalchemy import text

from app.db.base import Base  # noqa: F401  (registers all models)
from app.db.session import engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[init_db] extensions + tables + indexes created successfully")


if __name__ == "__main__":
    asyncio.run(main())
