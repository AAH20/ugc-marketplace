"""Tests for error handling middleware."""
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


def create_app_with_error_handler():
    """Create a minimal FastAPI app with error handling middleware for testing."""
    app = FastAPI()

    @app.middleware("http")
    async def error_handler_middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Bad request: {str(exc)}", "type": "value_error"},
            )
        except PermissionError as exc:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Forbidden: {str(exc)}", "type": "permission_error"},
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(exc)}", "type": "internal_error"},
            )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/error/value")
    async def trigger_value_error():
        raise ValueError("invalid input provided")

    @app.get("/error/permission")
    async def trigger_permission_error():
        raise PermissionError("insufficient permissions")

    @app.get("/error/generic")
    async def trigger_generic_error():
        raise RuntimeError("something went wrong")

    @app.get("/error/http-exception")
    async def trigger_http_exception():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Resource not found")

    return app


@pytest.fixture
def client():
    app = create_app_with_error_handler()
    return TestClient(app)


class TestErrorHandlerMiddleware:
    """Test suite for error handling middleware."""

    def test_successful_request_passes_through(self, client):
        """Successful requests should pass through the middleware unchanged."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_value_error_returns_400(self, client):
        """ValueError should be caught and return 400 Bad Request."""
        response = client.get("/error/value")
        assert response.status_code == 400
        assert response.json()["type"] == "value_error"
        assert "invalid input provided" in response.json()["detail"]

    def test_permission_error_returns_403(self, client):
        """PermissionError should be caught and return 403 Forbidden."""
        response = client.get("/error/permission")
        assert response.status_code == 403
        assert response.json()["type"] == "permission_error"
        assert "insufficient permissions" in response.json()["detail"]

    def test_generic_exception_returns_500(self, client):
        """Unhandled exceptions should return 500 Internal Server Error."""
        response = client.get("/error/generic")
        assert response.status_code == 500
        assert response.json()["type"] == "internal_error"
        assert "something went wrong" in response.json()["detail"]

    def test_error_response_is_json(self, client):
        """Error responses should be valid JSON with expected structure."""
        response = client.get("/error/value")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "type" in data

    def test_error_response_content_type(self, client):
        """Error responses should have application/json content type."""
        response = client.get("/error/value")
        assert response.status_code == 400
        assert "application/json" in response.headers["content-type"]
