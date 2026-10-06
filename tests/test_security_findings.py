"""Regression tests for the three bandit findings that CI previously masked.

Each test pins the *fixed* contract, so it fails against the vulnerable code.

B108 -- app/database.py hardcoded /tmp for the SQLite fallback. /tmp is
        world-writable, so another local user could pre-create the directory
        or symlink the file and hijack the database.
B104 -- config default host "0.0.0.0" binds every interface by default.
B608 -- restore_from_archive() interpolated table_name and JSON-derived column
        names straight into SQL text(), allowing SQL injection.
"""
from __future__ import annotations

import gzip
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


@pytest.fixture(autouse=True)
def _sqlite_env_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the SQLite fallback path for every test in this module.

    CI sets ``DATABASE_URL`` to Postgres at workflow level; ``get_database_url``
    treats that as authoritative over the SQLite fallback these tests pin. The
    contract under test B108 only applies to the fallback, so remove DATABASE_URL
    to exercise it deterministically regardless of the ambient environment.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)


# --------------------------------------------------------------------------
# B108 -- the SQLite fallback directory must not be world-writable
# --------------------------------------------------------------------------


def test_sqlite_data_dir_is_not_world_accessible() -> None:
    """The fallback data directory must be created 0o700, not 0o777.

    /tmp itself is sticky and world-writable. A pre-created directory there
    owned by another user, or a symlink pointing at a sensitive path, would
    otherwise let a local attacker control the database file.
    """
    from app import database

    base = Path(tempfile.mkdtemp())
    target = base / "data" / "ugc.db"
    database.configure_sqlite_path(str(target))
    try:
        database.get_engine()
    finally:
        database.reset_engine()

    assert target.parent.is_dir(), "data directory was not created"

    mode = stat.S_IMODE(target.parent.stat().st_mode)
    assert not (mode & stat.S_IWOTH), f"data dir is world-writable: {mode:04o}"
    assert not (mode & stat.S_IROTH), f"data dir is world-readable: {mode:04o}"
    assert mode & stat.S_IXUSR, f"data dir is not owner-executable: {mode:04o}"


def test_existing_insecure_data_dir_is_tightened() -> None:
    """A pre-existing world-writable directory must have its mode repaired.

    This is the actual attack: the directory already exists (created by
    another user or a previous run), so mkdir(exist_ok=True) does nothing and
    the loose permissions silently persist.
    """
    from app import database

    base = Path(tempfile.mkdtemp())
    data_dir = base / "data"
    data_dir.mkdir()
    os.chmod(data_dir, 0o777)

    target = data_dir / "ugc.db"
    database.configure_sqlite_path(str(target))
    try:
        database.get_engine()
    finally:
        database.reset_engine()

    mode = stat.S_IMODE(data_dir.stat().st_mode)
    assert not (mode & (stat.S_IWOTH | stat.S_IROTH)), (
        f"pre-existing insecure data dir was not tightened: {mode:04o}"
    )


def test_default_data_dir_is_configurable_not_hardcoded_tmp() -> None:
    """UGC_DATA_DIR must still override the location (no hardcoded /tmp)."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.database as d; print(d.get_database_url())",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "UGC_DATA_DIR": "/var/lib/ugc-marketplace",
            "DATABASE_URL": "",
        },
        timeout=60,
    )
    out = result.stdout.strip()
    assert out, f"no output: {result.stderr[-400:]}"
    assert "/var/lib/ugc-marketplace" in out, f"UGC_DATA_DIR ignored: {out}"


# --------------------------------------------------------------------------
# B104 -- the server must not bind all interfaces by default
# --------------------------------------------------------------------------


def test_default_host_is_not_all_interfaces() -> None:
    """settings.host must default to loopback, not 0.0.0.0."""
    sys.path.insert(0, str(SRC_ROOT))
    try:
        from ugc_marketplace.config import get_settings

        settings = get_settings()
    finally:
        sys.path.pop(0)

    assert settings.host not in {"0.0.0.0", "::"}, (
        f"default host binds every interface: {settings.host!r}"
    )
    assert settings.host in {"127.0.0.1", "localhost", "::1"}, (
        f"expected a loopback default, got {settings.host!r}"
    )


def test_host_is_still_env_overridable() -> None:
    """Explicit opt-in to 0.0.0.0 must remain possible for containers."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ugc_marketplace.config import get_settings; print(get_settings().host)",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(SRC_ROOT),
            "HOST": "0.0.0.0",
        },
        timeout=60,
    )
    assert result.returncode == 0, f"import failed: {result.stderr[-400:]}"
    assert result.stdout.strip() == "0.0.0.0", (
        f"HOST override no longer works: {result.stdout!r}"
    )


# --------------------------------------------------------------------------
# B608 -- restore_from_archive must reject injected identifiers
# --------------------------------------------------------------------------


def _make_archive(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "records.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return path


class _ExplodingEngine:
    """Fails loudly if any SQL is executed, proving validation runs first."""

    def begin(self):
        raise AssertionError("SQL was executed despite an invalid identifier")


@pytest.fixture()
def archival_manager():
    sys.path.insert(0, str(SRC_ROOT))
    try:
        from ugc_marketplace.database.archival import ArchivalManager
    finally:
        sys.path.pop(0)

    with tempfile.TemporaryDirectory() as td:
        yield ArchivalManager(_ExplodingEngine(), archive_dir=td)


@pytest.mark.parametrize(
    "bad_table",
    [
        "users; DROP TABLE users",
        "users WHERE 1=1",
        'users" ON CONFLICT DO NOTHING',
        "pg_catalog.pg_user",
    ],
)
@pytest.mark.asyncio
async def test_restore_rejects_malicious_table_name(archival_manager, tmp_path, bad_table):
    """A table name that is not a plain identifier must be refused."""
    archive = _make_archive(tmp_path, [{"id": 1}])

    with pytest.raises(ValueError) as exc:
        await archival_manager.restore_from_archive(str(archive), bad_table)

    assert "table" in str(exc.value).lower()


@pytest.mark.parametrize(
    "bad_column",
    [
        "id) VALUES (1); DROP TABLE users; --",
        "id, (SELECT password FROM users)",
    ],
)
@pytest.mark.asyncio
async def test_restore_rejects_malicious_column_name(archival_manager, tmp_path, bad_column):
    """A column name that is not a plain identifier must be refused."""
    archive = _make_archive(tmp_path, [{bad_column: 1}])

    with pytest.raises(ValueError) as exc:
        await archival_manager.restore_from_archive(str(archive), "events")

    assert "column" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_restore_accepts_valid_identifiers(archival_manager, tmp_path):
    """Ordinary identifiers must still pass validation.

    The engine explodes on use, so reaching the execute stage proves the
    identifier was accepted and the fix did not simply reject everything.
    """
    archive = _make_archive(tmp_path, [{"id": 1, "user_id": 2}])

    with pytest.raises(AssertionError, match="SQL was executed"):
        await archival_manager.restore_from_archive(str(archive), "analytics_events")
