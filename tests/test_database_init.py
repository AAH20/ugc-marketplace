"""init_db must serialize schema creation across concurrent workers.

With `uvicorn --workers N`, every worker runs the startup hook and calls
init_db(). SQLAlchemy's create_all is race-safe for tables (it checks the
catalog per table) but NOT for native PostgreSQL ENUM types: N workers can all
observe "commission_status missing" and then race on the CREATE TYPE, which
Postgres rejects with

    psycopg2.errors.UniqueViolation: duplicate key value violates unique
    constraint "pg_type_typname_nsp_index"

(observed in CD run 37452615409, smoke test, 4-worker container). The fix is to
take a transaction-scoped advisory lock around create_all on PostgreSQL, so
workers create the schema one at a time. SQLite (local fallback) needs no lock:
it is only ever a single-process file database in this app.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import make_url

from app import database


class _RecordingConn:
    """Captures SQL statements executed against it."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, stmt: Any, *args: Any, **kwargs: Any) -> None:
        self.statements.append(str(stmt))


class _RecordingEngine:
    """Minimal engine double: records begin() blocks and create_all binds."""

    def __init__(self, url: str) -> None:
        self.url = make_url(url)
        self.last_conn: _RecordingConn | None = None

    def begin(self) -> Any:
        conn = _RecordingConn()
        self.last_conn = conn

        class _Ctx:
            def __enter__(self) -> _RecordingConn:
                return conn

            def __exit__(self, *a: Any) -> None:
                return None

        return _Ctx()


@pytest.fixture()
def patched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch get_engine and capture create_all calls."""
    calls: dict[str, Any] = {"create_all_binds": []}

    def fake_create_all(*args: Any, **kwargs: Any) -> None:
        # Called as Base.metadata.create_all(bind=...): the instance-attribute
        # patch receives only the kwargs init_db passes, so recover the bind
        # from either the kwarg or the second positional slot.
        bind = kwargs.get("bind")
        if bind is None and len(args) > 1:
            bind = args[1]
        calls["create_all_binds"].append(bind)

    monkeypatch.setattr(database.Base.metadata, "create_all", fake_create_all)
    return calls


def test_init_db_takes_advisory_lock_on_postgres(
    monkeypatch: pytest.MonkeyPatch, patched: dict[str, Any]
) -> None:
    engine = _RecordingEngine("postgresql+asyncpg://user:pw@localhost:5432/db")
    monkeypatch.setattr(database, "get_engine", lambda: engine)

    database.init_db()

    conn = engine.last_conn
    assert conn is not None, "init_db must run create_all inside an engine.begin() block on Postgres"
    assert any("pg_advisory_xact_lock" in s for s in conn.statements), (
        f"no advisory lock taken; statements={conn.statements}"
    )
    assert patched["create_all_binds"], "create_all was not called"
    assert patched["create_all_binds"][-1] is conn, (
        "create_all must run on the same connection that holds the advisory lock"
    )


def test_init_db_skips_lock_on_sqlite(
    monkeypatch: pytest.MonkeyPatch, patched: dict[str, Any]
) -> None:
    engine = _RecordingEngine("sqlite:////tmp/ugc-test.db")
    monkeypatch.setattr(database, "get_engine", lambda: engine)

    database.init_db()

    assert patched["create_all_binds"], "create_all was not called"
    assert patched["create_all_binds"][-1] is engine, "sqlite path should create_all on the engine directly"
    # No begin() block was opened on the sqlite path.
    assert engine.last_conn is None


def test_init_db_is_callable_with_real_sqlite_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration guard: the sqlite fallback path still creates tables."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    database.reset_engine()
    try:
        database.init_db()
    finally:
        database.reset_engine()
