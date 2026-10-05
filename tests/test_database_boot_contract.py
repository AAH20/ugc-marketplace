"""Tests pinning the container boot contract that CD's smoke test exercises.

Root cause: in the runtime image the app runs as the non-root `app` user in
`/app`, which is not writable. With no DATABASE_URL set, app.database fell back
to a relative SQLite path and startup died with:

    sqlite3.OperationalError: unable to open database file
    ERROR: Application startup failed. Exiting.

These tests are subprocess-isolated (same reason as test_gtm_db_lazy.py):
importing app.database builds an engine, so it must not happen in-process.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(body: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Execute `body` in a clean interpreter with an isolated cwd."""
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    # Remove any inherited DATABASE_URL so we test the fallback path.
    env.pop("DATABASE_URL", None)
    if env_extra:
        env.update(env_extra)

    workdir = REPO_ROOT
    if env_extra and env_extra.get("__CWD__"):
        workdir = env_extra.pop("__CWD__")

    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        cwd=workdir,
        env=env,
        timeout=60,
    )


def test_default_url_is_absolute_and_writable() -> None:
    """The SQLite fallback must be an absolute path, not CWD-relative.

    A relative path resolves against the process working directory, which is
    read-only for the non-root `app` user in the runtime image.
    """
    result = _run(
        """
        import app.database as d
        url = d.get_database_url()
        assert url.startswith("sqlite"), f"expected sqlite fallback, got {url!r}"
        # Strip the driver prefix and assert we got an absolute filesystem path.
        path = url.split("///", 1)[-1]
        assert path.startswith("/"), f"SQLite path must be absolute, got {path!r}"
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-600:]!r}"


def test_sqlite_parent_directory_is_created() -> None:
    """The directory holding the SQLite file must be auto-created.

    Otherwise startup fails with 'unable to open database file' on any host
    where the data directory does not yet exist.
    """
    result = _run(
        """
        import os, tempfile, pathlib, app.database as d

        base = pathlib.Path(tempfile.mkdtemp())
        target = base / "nested" / "deeper" / "data.db"
        assert not target.parent.exists(), "precondition: parent dir must not exist"

        d.configure_sqlite_path(str(target))
        try:
            engine = d.get_engine()
            with engine.connect() as conn:
                conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        finally:
            d.reset_engine()

        assert target.exists(), f"sqlite file not created at {target}"
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-600:]!r}"


def test_database_url_env_var_wins() -> None:
    """An explicit DATABASE_URL must override the SQLite fallback.

    The async driver is mapped to its sync equivalent, because this module
    is synchronous SQLAlchemy.
    """
    result = _run(
        """
        import os
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost:5432/db"
        import app.database as d
        url = d.get_database_url()
        # Configured Postgres is honoured, but with a synchronous driver.
        assert url.startswith("postgresql+"), f"DATABASE_URL ignored; got {url!r}"
        assert "psycopg2" in url, f"expected sync driver, got {url!r}"
        print("OK")
        """,
        env_extra={"DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db"},
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-600:]!r}"
