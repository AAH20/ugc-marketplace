"""Tests for API routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.main import app


client = TestClient(app)


class TestPostRoutes:
    """Test post triggering routes."""

    def test_post_to_product_hunt(self):
        """POST /posts/product_hunt triggers a Product Hunt launch."""
        with patch("app.routes.posts.ProductHuntIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value={"id": "ph_123", "name": "Test"})
            mock_integration.return_value = mock_instance

            response = client.post("/api/v1/posts/product_hunt", json={
                "name": "Test Product",
                "tagline": "A test product",
                "url": "https://example.com",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "ph_123"
            assert data["platform"] == "product_hunt"

    def test_post_to_hacker_news(self):
        """POST /posts/hacker_news triggers a HN post."""
        with patch("app.routes.posts.HackerNewsIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value={"id": "hn_123", "title": "Test"})
            mock_integration.return_value = mock_instance

            response = client.post("/api/v1/posts/hacker_news", json={
                "title": "Test Post",
                "url": "https://example.com",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "hn_123"

    def test_post_to_reddit(self):
        """POST /posts/reddit triggers a Reddit submission."""
        with patch("app.routes.posts.RedditIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value={"id": "t3_abc", "title": "Test"})
            mock_integration.return_value = mock_instance

            response = client.post("/api/v1/posts/reddit", json={
                "title": "Test Post",
                "url": "https://example.com",
                "subreddit": "test",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "t3_abc"

    def test_post_to_twitter(self):
        """POST /posts/twitter triggers a tweet."""
        with patch("app.routes.posts.TwitterIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value={"id": "tweet_123", "text": "Hello"})
            mock_integration.return_value = mock_instance

            response = client.post("/api/v1/posts/twitter", json={
                "text": "Hello World!",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "tweet_123"

    def test_post_invalid_platform(self):
        """POST /posts/{platform} returns 404 for unknown platform."""
        response = client.post("/api/v1/posts/unknown_platform", json={
            "text": "Test",
        })
        assert response.status_code == 404

    def test_post_missing_required_fields(self):
        """POST /posts/{platform} returns 422 for missing fields."""
        response = client.post("/api/v1/posts/twitter", json={})
        assert response.status_code == 422

    def test_post_integration_error(self):
        """POST /posts/{platform} returns 502 on integration failure."""
        with patch("app.routes.posts.TwitterIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(side_effect=Exception("API error"))
            mock_integration.return_value = mock_instance

            response = client.post("/api/v1/posts/twitter", json={
                "text": "Test",
            })
            assert response.status_code == 502


class TestHealthRoutes:
    """Test health check routes."""

    def test_health_product_hunt(self):
        """GET /integrations/product_hunt/health returns status."""
        with patch("app.routes.posts.ProductHuntIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_integration.return_value = mock_instance

            response = client.get("/api/v1/integrations/product_hunt/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_hacker_news(self):
        """GET /integrations/hacker_news/health returns status."""
        with patch("app.routes.posts.HackerNewsIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_integration.return_value = mock_instance

            response = client.get("/api/v1/integrations/hacker_news/health")
            assert response.status_code == 200

    def test_health_reddit(self):
        """GET /integrations/reddit/health returns status."""
        with patch("app.routes.posts.RedditIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_integration.return_value = mock_instance

            response = client.get("/api/v1/integrations/reddit/health")
            assert response.status_code == 200

    def test_health_twitter(self):
        """GET /integrations/twitter/health returns status."""
        with patch("app.routes.posts.TwitterIntegration") as mock_integration:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_integration.return_value = mock_instance

            response = client.get("/api/v1/integrations/twitter/health")
            assert response.status_code == 200

    def test_health_invalid_platform(self):
        """GET /integrations/{platform}/health returns 404 for unknown platform."""
        response = client.get("/api/v1/integrations/unknown/health")
        assert response.status_code == 404
