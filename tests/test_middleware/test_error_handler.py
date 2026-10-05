"""Tests for ErrorHandlerMiddleware.

These assert the middleware's REAL response contract:

    {"error": {"code": ..., "message": ..., "details": {...}}}   # AppError subclasses
    {"error": {"code": "internal_error", "message": "An unexpected error occurred."}}

Note on scope: HTTPException is deliberately NOT handled by this middleware.
FastAPI's exception handler converts HTTPException into a ``{"detail": ...}``
response before it reaches user middleware, so a 404 from ``HTTPException``
keeps FastAPI's shape. That behaviour is pinned below so a future refactor
cannot silently change the public error envelope.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.error_handler import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ErrorHandlerMiddleware,
    NotFoundError,
    ValidationError,
)


def build_app() -> FastAPI:
    """App wired with the real middleware plus routes that raise each error type."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/error/not-found")
    async def raise_not_found():
        raise NotFoundError("content not found")

    @app.get("/error/not-found-with-details")
    async def raise_not_found_with_details():
        raise NotFoundError("content not found", details={"content_id": "c-1"})

    @app.get("/error/validation")
    async def raise_validation():
        raise ValidationError("amount must be positive")

    @app.get("/error/authentication")
    async def raise_authentication():
        raise AuthenticationError("missing credentials")

    @app.get("/error/authorization")
    async def raise_authorization():
        raise AuthorizationError("insufficient permissions")

    @app.get("/error/conflict")
    async def raise_conflict():
        raise ConflictError("duplicate email")

    @app.get("/error/http-exception")
    async def raise_http_exception():
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/error/unhandled")
    async def raise_unhandled():
        raise RuntimeError("something went wrong")

    return app


@pytest.fixture
def client():
    # raise_server_exceptions=False so unhandled errors reach the middleware
    # and get converted to a 500 JSONResponse instead of propagating.
    return TestClient(build_app(), raise_server_exceptions=False)


class TestErrorEnvelope:
    """The response envelope itself."""

    def test_success_passes_through_unchanged(self, client):
        """A successful response is not rewritten by the middleware."""
        response = client.get("/ok")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_app_error_body_shape(self, client):
        """Every AppError maps to {"error": {"code", "message"}}."""
        response = client.get("/error/validation")

        assert response.status_code == 422
        body = response.json()
        assert set(body) == {"error"}
        assert set(body["error"]) == {"code", "message"}
        assert body["error"]["code"] == "validation_error"
        assert body["error"]["message"] == "amount must be positive"

    def test_details_included_when_provided(self, client):
        """A non-empty details dict is nested under error.details."""
        response = client.get("/error/not-found-with-details")

        assert response.status_code == 404
        assert response.json()["error"]["details"] == {"content_id": "c-1"}

    def test_details_omitted_when_empty(self, client):
        """An empty/absent details dict must not add a 'details' key."""
        response = client.get("/error/not-found")

        assert response.status_code == 404
        assert "details" not in response.json()["error"]

    def test_content_type_is_json(self, client):
        """Error responses are served as application/json."""
        for path in ("/error/not-found", "/error/validation", "/error/unhandled"):
            response = client.get(path)
            assert "application/json" in response.headers["content-type"], path


class TestAppErrorStatusCodes:
    """Each AppError subclass carries its own status code and error code."""

    @pytest.mark.parametrize(
        ("path", "status_code", "error_code"),
        [
            ("/error/not-found", 404, "not_found"),
            ("/error/validation", 422, "validation_error"),
            ("/error/authentication", 401, "authentication_error"),
            ("/error/authorization", 403, "authorization_error"),
            ("/error/conflict", 409, "conflict"),
        ],
    )
    def test_status_and_code(self, client, path, status_code, error_code):
        response = client.get(path)

        assert response.status_code == status_code
        assert response.json()["error"]["code"] == error_code

    def test_app_error_message_is_passed_through(self, client):
        """The AppError message is surfaced verbatim in error.message."""
        response = client.get("/error/authorization")

        assert response.json()["error"]["message"] == "insufficient permissions"


class TestUnhandledException:
    """Non-AppError exceptions become a generic 500."""

    def test_unhandled_exception_returns_500(self, client):
        response = client.get("/error/unhandled")

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "internal_error"

    def test_unhandled_exception_does_not_leak_internals(self, client):
        """The original exception text must not reach the client."""
        response = client.get("/error/unhandled")

        body = response.json()
        assert body["error"]["message"] == "An unexpected error occurred."
        assert "something went wrong" not in response.text
        assert "RuntimeError" not in response.text


class TestHttpExceptionNotIntercepted:
    """HTTPException keeps FastAPI's own {"detail": ...} shape."""

    def test_http_exception_uses_fastapi_shape(self, client):
        response = client.get("/error/http-exception")

        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found"}


class TestExceptionHierarchy:
    """The exception classes' static metadata."""

    @pytest.mark.parametrize(
        ("exc_cls", "status_code", "error_code"),
        [
            (AppError, 500, "internal_error"),
            (NotFoundError, 404, "not_found"),
            (ValidationError, 422, "validation_error"),
            (AuthenticationError, 401, "authentication_error"),
            (AuthorizationError, 403, "authorization_error"),
            (ConflictError, 409, "conflict"),
        ],
    )
    def test_class_attributes(self, exc_cls, status_code, error_code):
        assert exc_cls.status_code == status_code
        assert exc_cls.error_code == error_code

    def test_all_errors_subclass_app_error(self):
        for exc_cls in (
            NotFoundError,
            ValidationError,
            AuthenticationError,
            AuthorizationError,
            ConflictError,
        ):
            assert issubclass(exc_cls, AppError)

    def test_details_defaults_to_empty_dict(self):
        assert AppError("boom").details == {}

    def test_details_defaults_to_empty_dict_when_explicit_none(self):
        assert AppError("boom", details=None).details == {}

    def test_message_is_str_arg(self):
        exc = AppError("boom", details={"a": 1})

        assert exc.message == "boom"
        assert exc.details == {"a": 1}
        assert str(exc) == "boom"