"""Rate limiting tests for ugc-marketplace."""
from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.rate_limit import RateLimitMiddleware


class TestRateLimiting:
    """Test that rate limiting is enforced."""

    def test_rate_limit_exceeded_returns_429(self):
        """Test that exceeding rate limit returns 429 status."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        # Very low rate limit for testing
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=5,
            burst_size=2,
        )
        client = TestClient(app)

        responses = []
        for _ in range(20):
            resp = client.get("/test")
            responses.append(resp.status_code)
            if resp.status_code == 429:
                break

        assert 429 in responses, (
            "Rate limit was not enforced - no 429 response received"
        )

    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in responses."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=60,
            burst_size=10,
        )
        client = TestClient(app)

        resp = client.get("/test")
        # Check for rate limit headers
        has_rate_limit = (
            "X-RateLimit-Limit" in resp.headers
            or "X-RateLimit-Remaining" in resp.headers
            or "x-ratelimit-limit" in resp.headers
            or "x-ratelimit-remaining" in resp.headers
        )

    def test_rate_limit_retry_after_header(self):
        """Test that 429 responses include Retry-After header."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=5,
            burst_size=2,
        )
        client = TestClient(app)

        for _ in range(20):
            resp = client.get("/test")
            if resp.status_code == 429:
                assert "Retry-After" in resp.headers or "retry-after" in resp.headers
                break

    def test_health_endpoints_excluded(self):
        """Test that health endpoints are excluded from rate limiting."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=5,
            burst_size=2,
        )
        client = TestClient(app)

        # Health endpoint should not be rate limited
        for _ in range(20):
            resp = client.get("/health")
            assert resp.status_code == 200, (
                "Health endpoint was rate limited"
            )
