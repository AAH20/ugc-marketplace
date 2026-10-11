"""Coverage-gap tests for the ``ugc_marketplace.middleware`` package.

The following middleware modules had zero references anywhere under ``tests/``:
``security_headers``, ``error_handler``, ``api_key``, ``metrics``, ``audit``
and ``sanitization``.  Pure helpers are exercised directly; the security
critical ones are also driven through a real Starlette app.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ugc_marketplace.middleware.api_key import APIKeyMiddleware
from ugc_marketplace.middleware.audit import AuditMiddleware
from ugc_marketplace.middleware.error_handler import (
    AppError,
    ErrorHandlerMiddleware,
    NotFoundError,
)
from ugc_marketplace.middleware.metrics import MetricsMiddleware
from ugc_marketplace.middleware.sanitization import SanitizationMiddleware
from ugc_marketplace.middleware.security_headers import SecurityHeadersMiddleware


def _request(path="/", method="GET", headers=None, client=("1.2.3.4", 1234)) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw,
        "client": client,
        "scheme": "http",
        "server": ("testserver", 80),
    }
    return Request(scope)


async def _ok(request):
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


def test_security_headers_are_added_to_response():
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert "Strict-Transport-Security" in response.headers


# ---------------------------------------------------------------------------
# ErrorHandlerMiddleware
# ---------------------------------------------------------------------------


def test_error_handler_maps_app_errors_and_unknown_errors():
    async def not_found(request):
        raise NotFoundError("gone", details={"id": "x"})

    async def crash(request):
        raise RuntimeError("kaboom")

    app = Starlette(routes=[Route("/missing", not_found), Route("/crash", crash)])
    app.add_middleware(ErrorHandlerMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    missing = client.get("/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert missing.json()["error"]["details"] == {"id": "x"}

    crashed = client.get("/crash")
    assert crashed.status_code == 500
    assert crashed.json()["error"]["code"] == "internal_error"


def test_app_error_defaults():
    err = AppError("boom")
    assert err.status_code == 500
    assert err.error_code == "internal_error"
    assert err.details == {}


# ---------------------------------------------------------------------------
# APIKeyMiddleware
# ---------------------------------------------------------------------------


def _api_key_app(**kwargs):
    app = Starlette(routes=[Route("/protected", _ok), Route("/health", _ok)])
    app.add_middleware(APIKeyMiddleware, **kwargs)
    return app


def test_api_key_requires_and_validates_key():
    app = _api_key_app(api_keys={"secret-key": {"name": "t", "scopes": ["read"]}})
    client = TestClient(app)

    assert client.get("/protected").status_code == 401
    assert client.get("/protected", headers={"X-API-Key": "wrong"}).status_code == 403
    assert client.get("/protected", headers={"X-API-Key": "secret-key"}).status_code == 200
    # Excluded path needs no key.
    assert client.get("/health").status_code == 200


def test_api_key_accepts_query_parameter_for_websockets():
    app = _api_key_app(api_keys={"secret-key": {"name": "t"}})
    client = TestClient(app)
    assert client.get("/protected?api_key=secret-key").status_code == 200


def test_api_key_rejects_expired_key():
    app = _api_key_app(
        api_keys={"expired": {"name": "t", "expires_at": 1}},
    )
    assert TestClient(app).get("/protected", headers={"X-API-Key": "expired"}).status_code == 403


# ---------------------------------------------------------------------------
# AuditMiddleware helpers
# ---------------------------------------------------------------------------


def test_audit_redacts_sensitive_headers():
    mw = AuditMiddleware(app=None)
    redacted = mw._redact_headers({"Authorization": "Bearer x", "X-Trace": "abc"})

    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["X-Trace"] == "abc"


def test_audit_client_info_prefers_forwarded_header():
    mw = AuditMiddleware(app=None)
    info = mw._get_client_info(
        _request(headers={"X-Forwarded-For": "9.9.9.9, 8.8.8.8", "User-Agent": "pytest"})
    )

    assert info["ip"] == "9.9.9.9"
    assert info["user_agent"] == "pytest"


# ---------------------------------------------------------------------------
# MetricsMiddleware helpers
# ---------------------------------------------------------------------------


def test_metrics_route_key_normalises_ids():
    mw = MetricsMiddleware(app=None)
    assert mw._get_route_key(_request("/api/v1/listings/123")) == "/api/v1/listings/{id}"
    assert mw._get_route_key(_request("/api/v1/listings")) == "/api/v1/listings"


def test_metrics_reporting_after_recording():
    mw = MetricsMiddleware(app=None)
    mw.request_count["GET:/x"] += 2
    mw.request_latency["GET:/x"].extend([0.01, 0.02])
    mw.error_count["GET:/x"] += 1
    mw.status_codes["500"] += 1

    metrics = mw.get_metrics()
    assert metrics["request_count"]["GET:/x"] == 2
    assert metrics["latency"]["GET:/x"]["count"] == 2
    assert metrics["latency"]["GET:/x"]["p95"] >= metrics["latency"]["GET:/x"]["min"]

    prom = mw.get_prometheus_format()
    assert "http_requests_total" in prom
    assert "http_responses_total" in prom


# ---------------------------------------------------------------------------
# SanitizationMiddleware helpers
# ---------------------------------------------------------------------------


def test_sanitization_strips_tags_and_injection():
    mw = SanitizationMiddleware(app=None)
    cleaned = mw._sanitize_string("<script>alert(1)</script>SELECT * FROM users")

    assert "<script>" not in cleaned
    assert "SELECT" not in cleaned.upper()


def test_sanitization_recurses_dicts_and_lists():
    mw = SanitizationMiddleware(app=None)
    cleaned = mw._sanitize_dict(
        {"a": "<b>x</b>", "nested": {"c": "<i>y</i>"}, "items": ["<u>z</u>", 1]}
    )

    assert "<b>" not in cleaned["a"]
    assert "<i>" not in cleaned["nested"]["c"]
    assert "<u>" not in cleaned["items"][0]
    assert cleaned["items"][1] == 1


def test_sanitization_rejects_oversized_body():
    app = Starlette(routes=[Route("/", _ok, methods=["POST"])])
    app.add_middleware(SanitizationMiddleware, max_body_size=5)

    response = TestClient(app).post("/", json={"hello": "world"})
    assert response.status_code == 413
