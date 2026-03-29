"""
Signal Hunter — Database Engine & Session Management

Provides async SQLAlchemy engine and session factory for Supabase Postgres.
All database access goes through sessions created by `get_db()`.

Connection string format for Supabase:
    postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

Uses connection pooling via Supabase's PgBouncer (port 6543).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Naming conventions for constraints — makes Alembic migrations cleaner
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = MetaData(naming_convention=convention)


def _build_database_url() -> str:
    """
    Build the async database URL from Supabase settings.

    Supabase exposes two connection modes:
    - Port 5432: direct (session mode) — use for migrations
    - Port 6543: pooled (transaction mode) — use for app connections

    We use 6543 (pooled) for the app and 5432 for Alembic migrations.
    """
    settings = get_settings()
    return settings.database_url


def get_engine() -> create_async_engine:
    """Create the async engine singleton."""
    url = _build_database_url()
    return create_async_engine(
        url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        # Supabase uses PgBouncer in transaction mode — prepared statements
        # are not supported. Disable asyncpg's statement cache.
        connect_args={"statement_cache_size": 0},
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the engine."""
    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an async database session.

    Usage in routes:
        @router.get("/stuff")
        async def get_stuff(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
