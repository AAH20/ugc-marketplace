"""Twitter/X integration using v2 API."""

from typing import Optional

import httpx

from app.integrations.base import BaseIntegration, IntegrationError, RateLimiter, RetryConfig


class TwitterConfig:
    """Twitter/X API configuration."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        bearer_token: str,
        api_url: str = "https://api.twitter.com/2",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        self.api_url = api_url


class TwitterIntegration(BaseIntegration):
    """Twitter/X integration using v2 API."""

    PLATFORM = "twitter"
    MAX_TWEET_LENGTH = 280

    def __init__(self, config: TwitterConfig, retry_config: Optional[RetryConfig] = None):
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
        """Make a request to the Twitter v2 API."""
        url = f"{self.config.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.bearer_token}",
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
        """Create a tweet."""
        text = content.get("text")
        if not text:
            raise IntegrationError("Twitter: text is required")
        if len(text) > self.MAX_TWEET_LENGTH:
            raise IntegrationError(f"Twitter: text exceeds {self.MAX_TWEET_LENGTH} characters")

        payload = {"text": text}
        if content.get("media_ids"):
            payload["media"] = {"media_ids": content["media_ids"]}

        result = await self._make_request("POST", "tweets", data=payload)

        tweet_data = result.get("data", {})
        if not tweet_data:
            raise IntegrationError("Twitter: no tweet data in response")

        return {
            "id": tweet_data.get("id"),
            "text": tweet_data.get("text"),
            "platform": self.PLATFORM,
        }

    async def health_check(self) -> dict:
        """Check Twitter API connectivity."""
        try:
            result = await self._make_request("GET", "users/me")
            if "data" in result:
                return {"status": "healthy", "platform": self.PLATFORM}
            return {
                "status": "unhealthy",
                "platform": self.PLATFORM,
                "error": "No data in response",
            }
        except Exception as e:
            return {"status": "unhealthy", "platform": self.PLATFORM, "error": str(e)}
