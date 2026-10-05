"""Database session management.

Design notes
------------
* ``DATABASE_URL`` is authoritative; SQLite is only the local-dev fallback.
* The SQLite fallback path is **absolute** and its parent directory is created
  on demand. A CWD-relative path (``sqlite:///./ugc_marketplace.db``) resolved
  against the read-only ``/app`` working directory of the non-root ``app``
  user in the runtime image, and startup died with::

      sqlite3.OperationalError: unable to open database file
      ERROR: Application startup failed. Exiting.

* The engine is created lazily and cached, so importing this module never
  opens a connection or requires a driver that may not be installed.
"""

from __future__ import annotations

import logging
import os
import stat
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401 - ensures all models registered with Base
from app.models.base import Base

logger = logging.getLogger(__name__)

# Absolute, writable location for the local-dev SQLite fallback. The default
# sits under /tmp (writable by the non-root runtime user) but the directory is
# created 0o700 -- see _ensure_sqlite_parent. Set UGC_DATA_DIR for a durable
# location such as /var/lib/ugc-marketplace in production.
# nosec B108 - /tmp is the only location writable by the non-root `app` user in
# the runtime image. _ensure_sqlite_parent creates it 0o700 and repairs the mode
# of a pre-existing directory, so the world-writable /tmp is not exploitable
# here. Production should set UGC_DATA_DIR to a durable private path.
_DATA_DIR = Path(os.environ.get("UGC_DATA_DIR", "/tmp/ugc-marketplace"))  # nosec B108
_DEFAULT_SQLITE_PATH = _DATA_DIR / "ugc_marketplace.db"

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


# Async driver -> sync driver. This module is synchronous SQLAlchemy
# (create_engine + sessionmaker), so an async driver such as asyncpg or
# aiosqlite would wrap the engine in a greenlet and every query would fail
# with "MissingGreenlet: greenlet_spawn has not been called".
_ASYNC_TO_SYNC_DRIVER = {
    "postgresql+asyncpg": "postgresql+psycopg2",
    "postgres+asyncpg": "postgresql+psycopg2",
    "sqlite+aiosqlite": "sqlite",
    "mysql+aiomysql": "mysql+pymysql",
    "mysql+asyncmy": "mysql+pymysql",
}


def normalise_database_url(url: str) -> str:
    """Rewrite an async driver URL to its synchronous equivalent.

    Args:
        url: A SQLAlchemy database URL.

    Returns:
        The URL with any known async driver swapped for its sync counterpart.
        URLs that are already synchronous are returned unchanged.
    """
    for async_driver, sync_driver in _ASYNC_TO_SYNC_DRIVER.items():
        if url.startswith(async_driver + "://"):
            return url.replace(async_driver + "://", sync_driver + "://", 1)
    return url


def get_database_url() -> str:
    """Return the configured database URL, normalised for the sync engine.

    Returns:
        ``DATABASE_URL`` (async drivers mapped to sync) when set, otherwise an
        absolute SQLite fallback URL.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return normalise_database_url(url)
    return f"sqlite:///{_DEFAULT_SQLITE_PATH}"


def _is_sqlite(url: str) -> bool:
    """Check whether a SQLAlchemy URL points at SQLite."""
    return url.startswith("sqlite")


def _ensure_sqlite_parent(url: str) -> None:
    """Create the parent directory for a file-backed SQLite URL.

    The directory is created 0o700 and an existing directory is tightened to
    match. The default location lives under /tmp, which is world-writable, so
    without this another local user could pre-create the directory (or leave a
    symlink in place of the database file) and control the database.

    Args:
        url: The SQLAlchemy database URL.
    """
    if not _is_sqlite(url):
        return

    # In-memory SQLite (":memory:") has no parent directory to create.
    _, _, path = url.partition("///")
    if not path or path == ":memory:":
        return

    parent = Path(path).parent
    if str(parent):
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # mkdir(exist_ok=True) is a no-op for an existing directory, so repair
        # the mode explicitly rather than assuming it was created by us.
        current = 0
        try:
            current = stat.S_IMODE(parent.stat().st_mode)
            if current & 0o077:
                parent.chmod(0o700)
        except OSError as exc:
            # A pre-existing directory we do not own cannot be chmod'ed.
            # Surface the problem instead of silently using loose permissions.
            # `mode` is reserved by Logger.warning, so the observed mode is
            # passed as `dir_mode`.
            logger.warning(
                "Could not restrict permissions on SQLite data directory",
                extra={"path": str(parent), "dir_mode": f"{current:04o}"},
                exc_info=exc,
            )


def configure_sqlite_path(path: str) -> None:
    """Point the SQLite fallback at an explicit path (used by tests).

    Args:
        path: Absolute or relative filesystem path for the SQLite file.
    """
    global _DEFAULT_SQLITE_PATH
    _DEFAULT_SQLITE_PATH = Path(path)
    reset_engine()


def get_engine() -> Engine:
    """Return the cached engine, creating it on first use.

    Returns:
        A SQLAlchemy :class:`Engine`.
    """
    global _engine
    if _engine is None:
        url = get_database_url()
        _ensure_sqlite_parent(url)
        kwargs: dict = {}
        if _is_sqlite(url):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the cached session factory.

    Returns:
        A :class:`sessionmaker` bound to :func:`get_engine`.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def reset_engine() -> None:
    """Drop the cached engine and session factory (used by tests)."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session.

    Yields:
        A SQLAlchemy :class:`Session`, closed on teardown.
    """
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables declared on :class:`Base`."""
    Base.metadata.create_all(bind=get_engine())
