"""Twitter/X posting wrapper."""
import httpx

API_URL = "https://api.twitter.com/2"
MAX_TWEET_LENGTH = 280


class TwitterClient:
    """Minimal Twitter/X API wrapper."""

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token

    async def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        url = f"{API_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, json=data, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def post_tweet(self, text: str) -> dict:
        if not text:
            raise ValueError("text is required")
        if len(text) > MAX_TWEET_LENGTH:
            raise ValueError(f"text exceeds {MAX_TWEET_LENGTH} characters")
        result = await self._make_request("POST", "tweets", data={"text": text})
        return result["data"]