"""Authentication bypass tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.auth import (
    JWTValidationMiddleware,
    APIKeyAuthMiddleware,
    CombinedAuthMiddleware,
    JWT_SECRET_KEY,
)


class TestAuthenticationBypass:
    """Test that authentication cannot be bypassed."""

    def test_invalid_jwt_token_rejected(self):
        """Test that invalid JWT tokens are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = JWTValidationMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        invalid_tokens = [
            "invalid_token",
            "Bearer invalid",
            "",
            "null",
        ]
        for token in invalid_tokens:
            resp = client.get(
                "/test",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code in (401, 403), (
                f"Invalid token '{token}' was accepted"
            )

    def test_expired_jwt_token_rejected(self):
        """Test that expired JWT tokens are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = JWTValidationMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        # Create an expired token manually
        import base64
        import json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "user-123", "roles": ["consumer"], "exp": 0}).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(b"invalidsignature").rstrip(b"=")
        expired_token = f"{header.decode()}.{payload.decode()}.{signature.decode()}"

        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code == 401, "Expired token was accepted"

    def test_invalid_api_key_rejected(self):
        """Test that invalid API keys are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = APIKeyAuthMiddleware(app)
        client = TestClient(app)

        invalid_keys = [
            "invalid_key",
            "wrong_key_123",
            "",
            "null",
        ]
        for key in invalid_keys:
            resp = client.get(
                "/test",
                headers={"X-API-Key": key}
            )
            assert resp.status_code in (401, 403), (
                f"Invalid API key '{key}' was accepted"
            )

    def test_malformed_auth_header(self):
        """Test that malformed auth headers are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = JWTValidationMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        malformed_headers = [
            "Basic dXNlcjpwYXNz",
            "Bearer",
            "Bearer ",
            "bearer token",
            "Token abc123",
        ]
        for header in malformed_headers:
            resp = client.get(
                "/test",
                headers={"Authorization": header}
            )
            assert resp.status_code in (401, 403), (
                f"Malformed auth header '{header}' was accepted"
            )

    def test_sql_injection_auth_bypass(self):
        """Test that SQL injection cannot bypass authentication."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = JWTValidationMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "admin'--",
        ]
        for payload in payloads:
            resp = client.get(
                "/test",
                headers={"Authorization": f"Bearer {payload}"}
            )
            assert resp.status_code in (401, 403), (
                f"SQL injection bypassed authentication: {payload}"
            )

    def test_no_auth_header(self):
        """Test that requests without auth headers are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = JWTValidationMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        resp = client.get("/test")
        assert resp.status_code in (401, 403), (
            "Request without auth header was accepted"
        )

    def test_combined_auth_no_credentials(self):
        """Test that combined auth rejects requests without credentials."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = CombinedAuthMiddleware(app, secret_key=JWT_SECRET_KEY)
        client = TestClient(app)

        resp = client.get("/test")
        assert resp.status_code in (401, 403), (
            "Request without credentials was accepted"
        )
