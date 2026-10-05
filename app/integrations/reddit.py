"""Reddit integration using PRAW (Python Reddit API Wrapper)."""
import asyncio
from typing import Optional

from app.integrations.base import BaseIntegration, IntegrationError, RateLimiter, RetryConfig


class RedditConfig:
    """Reddit OAuth and API configuration."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        user_agent: str = "ugc-marketplace/1.0",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.user_agent = user_agent


class RedditIntegration(BaseIntegration):
    """Reddit integration using PRAW for submissions."""

    PLATFORM = "reddit"

    def __init__(self, config: RedditConfig, retry_config: Optional[RetryConfig] = None):
        super().__init__(retry_config=retry_config)
        self.config = config
        self._reddit = None
        self.rate_limiter = RateLimiter(max_requests=3, window_seconds=60)

    def _get_reddit(self):
        """Get or create PRAW Reddit instance (synchronous)."""
        if self._reddit is None:
            try:
                import praw
            except ImportError:
                raise IntegrationError("PRAW library not installed. Run: pip install praw")

            self._reddit = praw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                username=self.config.username,
                password=self.config.password,
                user_agent=self.config.user_agent,
            )
        return self._reddit

    async def post(self, content: dict) -> dict:
        """Create a Reddit submission."""
        title = content.get("title")
        url = content.get("url")
        text = content.get("text")
        subreddit_name = content.get("subreddit")

        if not title:
            raise IntegrationError("Reddit: title is required")
        if not subreddit_name:
            raise IntegrationError("Reddit: subreddit is required")
        if not url and not text:
            raise IntegrationError("Reddit: either url or text is required")

        loop = asyncio.get_event_loop()

        def _submit():
            reddit = self._get_reddit()
            subreddit = reddit.subreddit(subreddit_name)
            if url:
                return subreddit.submit(title, url=url)
            else:
                return subreddit.submit(title, selftext=text)

        submission = await loop.run_in_executor(None, _submit)

        return {
            "id": submission.id,
            "title": submission.title,
            "url": submission.url,
            "permalink": submission.permalink,
            "subreddit": subreddit_name,
            "platform": self.PLATFORM,
        }

    async def health_check(self) -> dict:
        """Check Reddit API connectivity."""
        try:
            loop = asyncio.get_event_loop()

            def _check():
                reddit = self._get_reddit()
                return reddit.user.me()

            await loop.run_in_executor(None, _check)
            return {"status": "healthy", "platform": self.PLATFORM}
        except Exception as e:
            return {"status": "unhealthy", "platform": self.PLATFORM, "error": str(e)}
