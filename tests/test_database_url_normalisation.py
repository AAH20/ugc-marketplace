"""Regression tests: DATABASE_URL must be normalised for the sync engine.

`app/database.py` uses **sync** SQLAlchemy throughout (``create_engine`` +
``sessionmaker``), but the documented/CI value of ``DATABASE_URL`` is the
**async** form ``postgresql+asyncpg://``. Passing an async driver to
``create_engine`` builds a greenlet-wrapped engine and every request dies with::

    sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called

These tests pin the async -> sync driver mapping.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _normalise(url: str) -> subprocess.CompletedProcess:
    """Ask a clean interpreter what sync URL app.database derives from `url`."""
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    script = textwrap.dedent(
        f"""
        import os
        os.environ["DATABASE_URL"] = {url!r}
        import app.database as d
        print(d.get_database_url())
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )


def test_asyncpg_url_is_normalised_to_psycopg2() -> None:
    """postgresql+asyncpg -> postgresql+psycopg2 (the sync driver)."""
    result = _normalise("postgresql+asyncpg://u:p@localhost:5432/db")
    got = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr
    assert "psycopg2" in got, f"asyncpg not normalised to a sync driver; got {got!r}"
    assert "asyncpg" not in got, f"async driver leaked through: {got!r}"


def test_postgres_plain_url_is_preserved() -> None:
    """A plain postgres:// URL is already sync and must be left alone."""
    result = _normalise("postgresql://u:p@localhost:5432/db")
    got = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr
    assert got == "postgresql://u:p@localhost:5432/db", f"plain URL was rewritten: {got!r}"


def test_async_sqlite_url_is_normalised() -> None:
    """sqlite+aiosqlite -> sqlite (the stdlib sqlite3 driver)."""
    result = _normalise("sqlite+aiosqlite:///./somewhere.db")
    got = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr
    assert got.startswith("sqlite:"), f"sqlite URL mangled: {got!r}"
    assert "aiosqlite" not in got, f"async sqlite driver leaked through: {got!r}"


def test_engine_uses_a_sync_driver_when_available() -> None:
    """A built engine must be synchronous, never a greenlet-wrapped async one.

    Building a Postgres engine needs its driver installed, so this test only
    asserts when psycopg2 is importable; the URL mapping itself is already
    covered by the tests above and never requires the driver.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    script = textwrap.dedent(
        """
        import importlib.util, os
        if importlib.util.find_spec("psycopg2") is None:
            print("SKIP")
        else:
            os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost:5432/db"
            import app.database as d
            engine = d.get_engine()
            assert not engine.dialect.is_async, "engine is async but app/database.py is sync"
            assert engine.dialect.driver != "asyncpg", "asyncpg must not be used"
            print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )
    assert ("OK" in result.stdout) or ("SKIP" in result.stdout), (
        f"stdout={result.stdout!r} stderr={result.stderr[-600:]!r}"
    )


def test_no_async_surplus_driver_is_installed() -> None:
    """Guard: the sync Postgres driver must be a declared dependency.

    CI sets DATABASE_URL to the async form; the sync driver it maps to has to
    actually exist in the image, or every request fails at connect time.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    script = textwrap.dedent(
        """
        import pathlib, re, sys

        pyproject = pathlib.Path("pyproject.toml").read_text()
        block = pyproject.split("[project.optional-dependencies]", 1)[0]
        declared = set(re.findall(r'"([A-Za-z0-9_.-]+)\s*[><=~]', block))
        driver = "psycopg2-binary" if "psycopg2-binary" in declared else "psycopg2"
        assert driver in declared, (
            f"{driver} is not a declared runtime dependency; the asyncpg->sync "
            f"mapping would fail at connect time"
        )
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-600:]!r}"
