"""Standalone DB sanity test: connectivity, pgvector, table presence."""
import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as conn:
        version = (await conn.execute(text("SHOW server_version;"))).scalar()
        has_vector = (
            await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='vector';")
            )
        ).scalar()
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname='public' ORDER BY tablename;"
                )
            )
        ).scalars().all()

    print(f"[test_db] PostgreSQL version   : {version}")
    print(f"[test_db] pgvector extension  : {has_vector}")
    print(f"[test_db] tables              : {', '.join(tables)}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
