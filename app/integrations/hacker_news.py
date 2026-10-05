"""Hacker News integration via Algolia API."""

from typing import Optional

import httpx

from app.integrations.base import BaseIntegration, IntegrationError, RateLimiter, RetryConfig


class HackerNewsConfig:
    """Hacker News Algolia API configuration."""

    def __init__(
        self,
        api_key: str,
        app_id: str,
        username: str,
        password: str,
        api_url: str = "https://hn.algolia.com/api/v1",
    ):
        self.api_key = api_key
        self.app_id = app_id
        self.username = username
        self.password = password
        self.api_url = api_url


class HackerNewsIntegration(BaseIntegration):
    """Hacker News integration using Algolia Search API."""

    PLATFORM = "hacker_news"

    def __init__(self, config: HackerNewsConfig, retry_config: Optional[RetryConfig] = None):
        super().__init__(retry_config=retry_config)
        self.config = config
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make a request to the Algolia HN API."""
        url = f"{self.config.api_url}/{endpoint}"
        headers = {
            "X-Algolia-Application-Id": self.config.app_id,
            "X-Algolia-API-Key": self.config.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
            elif method == "POST":
                response = await client.post(
                    url, json=data, headers=headers, params=params, timeout=30.0
                )
            else:
                raise IntegrationError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

    async def post(self, content: dict) -> dict:
        """Create a Hacker News story/post."""
        title = content.get("title")
        url = content.get("url")
        text = content.get("text")

        if not title:
            raise IntegrationError("Hacker News: title is required")

        # HN stories need either a URL or text
        if not url and not text:
            raise IntegrationError("Hacker News: either url or text is required")

        payload = {
            "title": title,
            "author": self.config.username,
        }
        if url:
            payload["url"] = url
        if text:
            payload["text"] = text

        result = await self._make_request("POST", "stories", data=payload)

        return {
            "id": result.get("objectID"),
            "title": result.get("title"),
            "url": result.get("url"),
            "author": result.get("author"),
            "points": result.get("points", 0),
            "created_at": result.get("created_at"),
            "platform": self.PLATFORM,
        }

    async def health_check(self) -> dict:
        """Check HN API connectivity."""
        try:
            result = await self._make_request(
                "GET", "search", params={"query": "test", "hitsPerPage": 1}
            )
            if "hits" in result:
                return {"status": "healthy", "platform": self.PLATFORM}
            return {
                "status": "unhealthy",
                "platform": self.PLATFORM,
                "error": "Unexpected response",
            }
        except Exception as e:
            return {"status": "unhealthy", "platform": self.PLATFORM, "error": str(e)}
