"""Tests for Reddit integration using PRAW."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.reddit import RedditIntegration, RedditConfig


class TestRedditConfig:
    """Test Reddit configuration."""

    def test_config_stores_credentials(self):
        config = RedditConfig(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
            user_agent="test_agent",
        )
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.username == "test_user"
        assert config.user_agent == "test_agent"


class TestRedditIntegration:
    """Test Reddit integration."""

    @pytest.fixture
    def config(self):
        return RedditConfig(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
            user_agent="test_agent",
        )

    @pytest.fixture
    def integration(self, config):
        return RedditIntegration(config)

    @pytest.mark.asyncio
    async def test_health_check_success(self, integration):
        """Health check returns healthy when API is reachable."""
        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_reddit.return_value.user.me = MagicMock(return_value="test_user")
            result = await integration.health_check()
            assert result["status"] == "healthy"
            assert result["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, integration):
        """Health check returns unhealthy when API fails."""
        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_reddit.side_effect = Exception("Reddit API down")
            result = await integration.health_check()
            assert result["status"] == "unhealthy"
            assert result["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_post_creates_submission(self, integration):
        """Post creates a Reddit submission."""
        mock_submission = MagicMock()
        mock_submission.id = "t3_abc123"
        mock_submission.title = "Test Post"
        mock_submission.url = "https://example.com"
        mock_submission.permalink = "/r/test/comments/abc123/test_post/"

        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.submit = MagicMock(return_value=mock_submission)
            mock_reddit.return_value.subreddit = MagicMock(return_value=mock_subreddit)

            result = await integration.post({
                "title": "Test Post",
                "url": "https://example.com",
                "subreddit": "test",
            })
            assert result["id"] == "t3_abc123"
            assert result["title"] == "Test Post"
            assert result["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_post_self_post(self, integration):
        """Post can create a self/text post."""
        mock_submission = MagicMock()
        mock_submission.id = "t3_def456"
        mock_submission.title = "Ask Reddit: Test?"
        mock_submission.selftext = "This is a self post"
        mock_submission.permalink = "/r/test/comments/def456/ask_reddit_test/"

        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.submit = MagicMock(return_value=mock_submission)
            mock_reddit.return_value.subreddit = MagicMock(return_value=mock_subreddit)

            result = await integration.post({
                "title": "Ask Reddit: Test?",
                "text": "This is a self post",
                "subreddit": "test",
            })
            assert result["id"] == "t3_def456"
            assert result["title"] == "Ask Reddit: Test?"

    @pytest.mark.asyncio
    async def test_post_requires_subreddit(self, integration):
        """Post requires a subreddit."""
        with pytest.raises(Exception):
            await integration.post({"title": "Test", "url": "https://example.com"})

    @pytest.mark.asyncio
    async def test_post_requires_title(self, integration):
        """Post requires a title."""
        with pytest.raises(Exception):
            await integration.post({"url": "https://example.com", "subreddit": "test"})

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, integration):
        """Rate limiter is applied to requests."""
        assert integration.rate_limiter is not None
        assert integration.rate_limiter.max_requests > 0

    @pytest.mark.asyncio
    async def test_post_handles_api_errors(self, integration):
        """Post raises IntegrationError on API errors."""
        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_reddit.side_effect = Exception("Reddit API error")
            with pytest.raises(Exception):
                await integration.post({
                    "title": "Test",
                    "url": "https://example.com",
                    "subreddit": "test",
                })

    @pytest.mark.asyncio
    async def test_post_includes_subreddit(self, integration):
        """Post targets the correct subreddit."""
        mock_submission = MagicMock()
        mock_submission.id = "t3_ghi789"
        mock_submission.title = "Test"
        mock_submission.permalink = "/r/test/comments/ghi789/test/"

        with patch.object(integration, "_get_reddit", new_callable=MagicMock) as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.submit = MagicMock(return_value=mock_submission)
            mock_reddit.return_value.subreddit = MagicMock(return_value=mock_subreddit)

            await integration.post({
                "title": "Test",
                "url": "https://example.com",
                "subreddit": "test",
            })
            mock_reddit.return_value.subreddit.assert_called_with("test")
