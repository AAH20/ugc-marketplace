"""Tests for Twitter/X integration using v2 API."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.twitter import TwitterIntegration, TwitterConfig


class TestTwitterConfig:
    """Test Twitter configuration."""

    def test_config_stores_credentials(self):
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret",
            bearer_token="test_bearer",
        )
        assert config.api_key == "test_key"
        assert config.api_secret == "test_secret"
        assert config.access_token == "test_token"
        assert config.bearer_token == "test_bearer"


class TestTwitterIntegration:
    """Test Twitter/X integration."""

    @pytest.fixture
    def config(self):
        return TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret",
            bearer_token="test_bearer",
        )

    @pytest.fixture
    def integration(self, config):
        return TwitterIntegration(config)

    @pytest.mark.asyncio
    async def test_health_check_success(self, integration):
        """Health check returns healthy when API is reachable."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"id": "123", "username": "test_user"}}
            result = await integration.health_check()
            assert result["status"] == "healthy"
            assert result["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, integration):
        """Health check returns unhealthy when API fails."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Twitter API down")
            result = await integration.health_check()
            assert result["status"] == "unhealthy"
            assert result["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_post_creates_tweet(self, integration):
        """Post creates a tweet."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "data": {
                    "id": "tweet_123",
                    "text": "Hello World!",
                }
            }
            result = await integration.post({"text": "Hello World!"})
            assert result["id"] == "tweet_123"
            assert result["text"] == "Hello World!"
            assert result["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_post_requires_text(self, integration):
        """Post requires text content."""
        with pytest.raises(Exception):
            await integration.post({})

    @pytest.mark.asyncio
    async def test_post_enforces_character_limit(self, integration):
        """Post enforces Twitter's 280 character limit."""
        with pytest.raises(Exception):
            await integration.post({"text": "x" * 281})

    @pytest.mark.asyncio
    async def test_post_handles_api_errors(self, integration):
        """Post raises IntegrationError on API errors."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Twitter API error")
            with pytest.raises(Exception):
                await integration.post({"text": "Test"})

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, integration):
        """Rate limiter is applied to requests."""
        assert integration.rate_limiter is not None
        assert integration.rate_limiter.max_requests > 0

    @pytest.mark.asyncio
    async def test_post_includes_auth(self, integration):
        """Requests include OAuth2 Bearer token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "123", "text": "Test"}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.twitter.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await integration.post({"text": "Test"})
            call_kwargs = mock_client.return_value.__aenter__.return_value.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test_bearer"

    @pytest.mark.asyncio
    async def test_post_with_media(self, integration):
        """Post can include media IDs."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "data": {"id": "tweet_456", "text": "Check this out!"}
            }
            result = await integration.post({
                "text": "Check this out!",
                "media_ids": ["media_123"],
            })
            assert result["id"] == "tweet_456"
