"""Async database session for GTM module.

Design notes
------------
The engine is created **lazily** and cached. Creating it at import time made
the whole application unimportable when the configured driver's DBAPI package
was absent (this crashed the CD smoke test with
``ModuleNotFoundError: No module named 'aiosqlite'``), and it silently used
SQLite even when ``DATABASE_URL`` pointed at Postgres.

``DATABASE_URL`` is authoritative. SQLite is only the local-dev fallback.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Local-dev fallback only. Never used when DATABASE_URL is set.
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./ugc_marketplace.db"

_engine = None
_session_factory: async_sessionmaker | None = None


def get_database_url() -> str:
    """Return the configured database URL.

    Returns:
        The ``DATABASE_URL`` environment variable if set, otherwise the
        SQLite local-dev fallback.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or DEFAULT_DATABASE_URL


def get_engine():
    """Return the cached async engine, creating it on first use.

    Returns:
        A SQLAlchemy ``AsyncEngine``.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_database_url(), echo=False, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Return the cached async session factory.

    Returns:
        An ``async_sessionmaker`` bound to :func:`get_engine`.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_gtm_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an :class:`AsyncSession`.

    Yields:
        An async database session, closed on teardown.
    """
    async with get_session_factory()() as session:
        yield session


def reset_engine() -> None:
    """Drop the cached engine/session factory (used by tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
