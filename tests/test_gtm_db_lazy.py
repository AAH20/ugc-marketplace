"""GTM database module must be lazy and must honour DATABASE_URL.

These tests pin the two defects that crashed the container in CD:
  1. Importing the module must NOT eagerly build an engine (that import raised
     ``ModuleNotFoundError: No module named 'aiosqlite'`` in the runtime image).
  2. ``DATABASE_URL`` must actually be used, not hardcoded SQLite.

Isolation note
--------------
These checks deliberately run in **subprocesses**. Reloading ``app.gtm.db``
in-process mutated shared module state and seeded rows into the SQLite file,
which leaked into unrelated test modules (video route tests saw phantom rows
like 'Product Showcase'). A subprocess gives each assertion a pristine
interpreter, so this file cannot pollute the rest of the suite.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(body: str) -> subprocess.CompletedProcess:
    """Execute `body` in a clean interpreter and return the completed process."""
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )


def test_import_does_not_require_aiosqlite_driver() -> None:
    """Importing app.gtm.db must not eagerly import a DBAPI driver.

    Blocks aiosqlite so an eager sqlite engine would raise ModuleNotFoundError,
    then imports the module and asserts the lazy accessor exists.
    """
    result = _run(
        """
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "aiosqlite":
                raise ModuleNotFoundError("No module named 'aiosqlite'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            import app.gtm.db as m
        finally:
            builtins.__import__ = real_import

        assert hasattr(m, "get_engine"), "expected a lazy get_engine() accessor"
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-800:]!r}"


def test_database_url_is_honoured() -> None:
    """DATABASE_URL must win over the hardcoded SQLite fallback."""
    result = _run(
        """
        import os
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost:5432/db"
        import app.gtm.db as m
        url = m.get_database_url()
        assert "postgresql+asyncpg" in url, f"DATABASE_URL ignored; got {url!r}"
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-800:]!r}"


def test_engine_is_cached_singleton() -> None:
    """Repeated get_engine() calls must reuse one pooled engine."""
    result = _run(
        """
        import os
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost:5432/db"
        import app.gtm.db as m
        assert m.get_engine() is m.get_engine(), "engine not cached"
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-800:]!r}"


def test_get_session_is_async_generator() -> None:
    """The FastAPI dependency must remain an async generator."""
    result = _run(
        """
        import inspect
        import app.gtm.db as m
        assert inspect.isasyncgenfunction(m.get_gtm_session)
        print("OK")
        """
    )
    assert "OK" in result.stdout, f"stdout={result.stdout!r} stderr={result.stderr[-800:]!r}"
