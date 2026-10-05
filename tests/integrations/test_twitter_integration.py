"""Tests for Twitter/X posting wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app import models  # noqa: F401
from app.integrations.twitter_integration import TwitterClient


class TestTwitterClient:
    """Test Twitter/X posting wrapper."""

    @pytest.fixture
    def client(self):
        return TwitterClient(bearer_token="test_bearer")

    @pytest.mark.asyncio
    async def test_post_tweet_success(self, client):
        """post_tweet returns tweet data on success."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"id": "123", "text": "Hello World!"}}
            result = await client.post_tweet("Hello World!")
            assert result["id"] == "123"
            assert result["text"] == "Hello World!"

    @pytest.mark.asyncio
    async def test_post_tweet_requires_text(self, client):
        """post_tweet raises ValueError when text is empty."""
        with pytest.raises(ValueError):
            await client.post_tweet("")

    @pytest.mark.asyncio
    async def test_post_tweet_enforces_character_limit(self, client):
        """post_tweet raises ValueError when text exceeds 280 chars."""
        with pytest.raises(ValueError):
            await client.post_tweet("x" * 281)

    @pytest.mark.asyncio
    async def test_post_tweet_sends_correct_payload(self, client):
        """post_tweet sends correct JSON payload to API."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"id": "456", "text": "Test"}}
            await client.post_tweet("Test")
            mock_req.assert_called_once_with(
                "POST", "tweets", data={"text": "Test"}
            )

    @pytest.mark.asyncio
    async def test_post_tweet_includes_auth_header(self, client):
        """post_tweet includes Bearer token in request headers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "789", "text": "Auth test"}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.twitter_integration.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )
            await client.post_tweet("Auth test")
            call_kwargs = mock_client.return_value.__aenter__.return_value.request.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test_bearer"
