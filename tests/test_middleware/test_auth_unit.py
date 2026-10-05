"""Tests for authentication middleware."""
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


def create_app_with_auth():
    """Create a minimal FastAPI app with auth middleware for testing."""
    app = FastAPI()

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip auth for public paths
        public_paths = ["/health", "/docs", "/openapi.json"]
        if request.url.path in public_paths:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )

        token = auth_header.replace("Bearer ", "")
        if token != "valid-token":
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid token"},
            )

        response = await call_next(request)
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected():
        return {"message": "secret data"}

    return app


@pytest.fixture
def client():
    app = create_app_with_auth()
    return TestClient(app)


class TestAuthMiddleware:
    """Test suite for authentication middleware."""

    def test_public_path_no_auth_required(self, client):
        """Public paths should be accessible without authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_protected_path_without_auth_header(self, client):
        """Protected paths should return 401 when no auth header is present."""
        response = client.get("/protected")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_protected_path_with_invalid_token(self, client):
        """Protected paths should return 403 for invalid tokens."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid token"

    def test_protected_path_with_valid_token(self, client):
        """Protected paths should be accessible with a valid token."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        assert response.json() == {"message": "secret data"}

    def test_protected_path_with_malformed_auth_header(self, client):
        """Malformed auth headers should return 401."""
        response = client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat token123"},
        )
        assert response.status_code == 401

    def test_protected_path_with_empty_bearer_token(self, client):
        """Empty bearer token should return 403."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 403
