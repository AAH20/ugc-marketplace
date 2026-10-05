"""Tests for Hacker News integration via Algolia API."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.hacker_news import HackerNewsIntegration, HackerNewsConfig


class TestHackerNewsConfig:
    """Test HN configuration."""

    def test_config_stores_api_key(self):
        config = HackerNewsConfig(
            api_key="test_key",
            app_id="test_app",
            username="test_user",
            password="test_pass",
        )
        assert config.api_key == "test_key"
        assert config.app_id == "test_app"
        assert config.username == "test_user"

    def test_config_default_api_url(self):
        config = HackerNewsConfig(
            api_key="test_key",
            app_id="test_app",
            username="test_user",
            password="test_pass",
        )
        assert "algolia" in config.api_url


class TestHackerNewsIntegration:
    """Test Hacker News integration."""

    @pytest.fixture
    def config(self):
        return HackerNewsConfig(
            api_key="test_key",
            app_id="test_app",
            username="test_user",
            password="test_pass",
        )

    @pytest.fixture
    def integration(self, config):
        return HackerNewsIntegration(config)

    @pytest.mark.asyncio
    async def test_health_check_success(self, integration):
        """Health check returns healthy when API is reachable."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"hits": [], "nbHits": 0}
            result = await integration.health_check()
            assert result["status"] == "healthy"
            assert result["platform"] == "hacker_news"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, integration):
        """Health check returns unhealthy when API fails."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("API down")
            result = await integration.health_check()
            assert result["status"] == "unhealthy"
            assert result["platform"] == "hacker_news"

    @pytest.mark.asyncio
    async def test_post_creates_item(self, integration):
        """Post creates a HN item via Algolia."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "objectID": "hn_123",
                "title": "Test Post",
                "url": "https://example.com",
                "author": "test_user",
                "points": 1,
            }
            result = await integration.post({
                "title": "Test Post",
                "url": "https://example.com",
                "text": "Optional text",
            })
            assert result["id"] == "hn_123"
            assert result["title"] == "Test Post"

    @pytest.mark.asyncio
    async def test_post_uses_correct_endpoint(self, integration):
        """Post uses the correct Algolia endpoint."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"objectID": "123"}
            await integration.post({"title": "Test", "url": "https://example.com"})
            call_args = mock_req.call_args
            assert "stories" in str(call_args) or "items" in str(call_args)

    @pytest.mark.asyncio
    async def test_post_handles_api_errors(self, integration):
        """Post raises IntegrationError on API errors."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Algolia error")
            with pytest.raises(Exception):
                await integration.post({"title": "Test"})

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, integration):
        """Rate limiter is applied to requests."""
        assert integration.rate_limiter is not None
        assert integration.rate_limiter.max_requests > 0

    @pytest.mark.asyncio
    async def test_post_includes_auth(self, integration):
        """Requests include Algolia auth headers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"objectID": "123"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.hacker_news.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await integration.post({"title": "Test", "url": "https://example.com"})
            call_kwargs = mock_client.return_value.__aenter__.return_value.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("X-Algolia-Application-Id") == "test_app"
            assert headers.get("X-Algolia-API-Key") == "test_key"

    @pytest.mark.asyncio
    async def test_post_story_without_url(self, integration):
        """Post can create a text-only story."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "objectID": "hn_456",
                "title": "Ask HN: Test?",
                "author": "test_user",
            }
            result = await integration.post({
                "title": "Ask HN: Test?",
                "text": "This is a text post",
            })
            assert result["id"] == "hn_456"
            assert result["title"] == "Ask HN: Test?"
