"""Bootstrap guard: the application must actually be importable.

This is the test whose absence let a fatal defect hide behind a green suite.

``ugc_marketplace/api/payments.py`` began with a stray
``from datetime import timezone`` placed *above* the module docstring and the
``from __future__ import annotations`` line, which Python rejects with::

    SyntaxError: from __future__ imports must occur at the beginning of the file

Because ``ugc_marketplace.main`` imports ``api.routes``, which imports
``api.payments``, the whole application was unimportable — ``uvicorn
ugc_marketplace.main:app`` could not start.

The existing suite never imported ``main`` (it exercised routers and services
directly), so ~1000 tests passed while the application was dead on arrival.

These tests pin the app's importability so a syntax/import break in any router
fails CI instead of hiding.
"""

from __future__ import annotations

import importlib


def test_app_module_is_importable():
    """The ASGI app module must import cleanly (it raised SyntaxError before)."""
    module = importlib.import_module("ugc_marketplace.main")

    assert module is not None


def test_app_object_exists_and_has_routes():
    """Importing main must yield a real ASGI app with routes mounted."""
    module = importlib.import_module("ugc_marketplace.main")

    app = getattr(module, "app", None)
    assert app is not None, "main module exposes no `app` object"
    assert getattr(app, "routes", None), "app has no routes mounted"


def test_payments_router_is_mounted():
    """The payments router must be part of the real app (the module that broke).

    Checks the OpenAPI schema rather than ``app.routes``: on this FastAPI
    version ``app.routes`` yields ``_IncludedRouter`` wrappers with no ``path``
    attribute, so inspecting it under-reports mounted routes.
    """
    module = importlib.import_module("ugc_marketplace.main")
    paths = set(module.app.openapi().get("paths", {}))

    assert any("payments" in p for p in paths), (
        f"payments routes missing from the app; sample paths: {sorted(paths)[:10]}"
    )
