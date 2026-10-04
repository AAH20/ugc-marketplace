"""Authorization bypass tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.auth import (
    RBACMiddleware,
    JWT_SECRET_KEY,
    UserRole,
)


class TestAuthorizationBypass:
    """Test that authorization cannot be bypassed."""

    def _create_token(self, roles):
        """Helper to create a JWT token with specific roles."""
        import base64
        import json
        import hmac
        import hashlib

        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload_data = {
            "sub": "user-123",
            "roles": roles,
            "exp": 9999999999,
        }
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET_KEY.encode(), f"{header.decode()}.{payload.decode()}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=")
        return f"{header.decode()}.{payload.decode()}.{signature.decode()}"

    def test_consumer_cannot_access_moderation(self):
        """Test that consumers cannot access moderation endpoints."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.MODERATOR],
        )
        client = TestClient(app)

        token = self._create_token(["consumer"])
        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            "Consumer accessed moderator endpoint"
        )

    def test_creator_cannot_access_admin(self):
        """Test that creators cannot access admin endpoints."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.ADMIN],
        )
        client = TestClient(app)

        token = self._create_token(["creator"])
        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            "Creator accessed admin endpoint"
        )

    def test_guest_cannot_access_creator_endpoints(self):
        """Test that guests cannot access creator endpoints."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.CREATOR],
        )
        client = TestClient(app)

        token = self._create_token(["guest"])
        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            "Guest accessed creator endpoint"
        )

    def test_admin_can_access_all(self):
        """Test that admins can access all endpoints."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.MODERATOR],
        )
        client = TestClient(app)

        token = self._create_token(["admin"])
        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, (
            "Admin was denied access to moderator endpoint"
        )

    def test_role_hierarchy_inheritance(self):
        """Test that role hierarchy is properly enforced."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.CONSUMER],
        )
        client = TestClient(app)

        # Admin should be able to access consumer endpoints
        token = self._create_token(["admin"])
        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, (
            "Admin was denied access to consumer endpoint"
        )

    def test_no_roles_rejected(self):
        """Test that requests without roles are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RBACMiddleware(
            app,
            required_roles=[UserRole.CONSUMER],
        )
        client = TestClient(app)

        # Create token without roles
        import base64
        import json
        import hmac
        import hashlib

        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload_data = {
            "sub": "user-123",
            "exp": 9999999999,
        }
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET_KEY.encode(), f"{header.decode()}.{payload.decode()}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=")
        token = f"{header.decode()}.{payload.decode()}.{signature.decode()}"

        resp = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code in (401, 403), (
            "Request without roles was accepted"
        )
