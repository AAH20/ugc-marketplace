"""Guard the test-suite bootstrap.

``tests/conftest.py`` imports the app from the top-level ``app`` package
(``app.main:app``), not from ``src/ugc_marketplace``. Both packages exist in
this repo and are distinct, so the distinction is easy to break silently: rename
or move ``app/`` and every test errors at collection with an ImportError.

These tests assert the resolution explicitly so the breakage is named rather
than showing up as a wall of collection errors.
"""

from __future__ import annotations

import importlib
import importlib.util

from fastapi import FastAPI


def test_conftest_app_package_resolves():
    """The top-level ``app`` package must be importable from the repo root."""
    spec = importlib.util.find_spec("app")
    assert spec is not None, (
        "top-level 'app' package not found — tests/conftest.py imports "
        "'app.main', which is resolved via pythonpath=['.'] in pyproject.toml"
    )
    assert spec.origin and spec.origin.endswith("app/__init__.py"), (
        f"'app' resolved to an unexpected location: {spec.origin}"
    )


def test_conftest_app_main_module_resolves():
    """``from app.main import app`` — the exact import conftest performs."""
    module = importlib.import_module("app.main")
    assert isinstance(module.app, FastAPI), (
        "app.main.app should be a FastAPI instance"
    )
    assert module.app.routes, "app.main.app has no routes mounted"


def test_conftest_supporting_imports_resolve():
    """Every symbol tests/conftest.py imports must exist."""
    base = importlib.import_module("app.models.base")
    assert hasattr(base, "Base"), "app.models.base.Base missing"

    database = importlib.import_module("app.database")
    assert hasattr(database, "get_db"), (
        "app.database.get_db missing — conftest overrides this dependency"
    )

    # Ensures all models are registered with Base before create_all() runs.
    importlib.import_module("app.models")


def test_client_fixture_works(client):
    """The client fixture backed by app.main.app can serve a request."""
    response = client.get("/health")
    assert response.status_code == 200, (
        f"/health returned {response.status_code}; app.main.app may not be the "
        "instance the fixtures are bound to"
    )