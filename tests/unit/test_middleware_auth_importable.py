"""Regression guard: ``ugc_marketplace.middleware.auth`` must be importable.

It previously began with ``import jwt`` (PyJWT), which is not a declared
dependency of this project — the codebase standard is python-jose
(``from jose import JWTError, jwt``, as used by ``security/auth.py``). PyJWT
is absent from the environment, so importing this module raised
``ModuleNotFoundError: No module named 'jwt'``: a landmine for any future
importer and a silent divergence from the rest of the package.

These tests pin the module to the codebase's JWT library so the divergence
cannot come back.
"""

from __future__ import annotations

import importlib


def test_middleware_auth_module_is_importable():
    """The module must import cleanly (it raised ModuleNotFoundError before)."""
    module = importlib.import_module("ugc_marketplace.middleware.auth")

    assert module is not None


def test_middleware_auth_resolves_jwt_from_python_jose():
    """The module must use python-jose, not PyJWT, matching security/auth.py."""
    module = importlib.import_module("ugc_marketplace.middleware.auth")

    # ``jose.jwt`` exposes ExpiredSignatureError and JWTError; PyJWT's ``jwt``
    # module has a different name and a different exception surface.
    assert module.jwt.__name__.startswith("jose")
    assert hasattr(module.jwt, "ExpiredSignatureError")
    assert hasattr(module.jwt, "JWTError")
