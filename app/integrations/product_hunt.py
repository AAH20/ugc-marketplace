"""Product Hunt integration via GraphQL API."""

from typing import Optional

import httpx

from app.integrations.base import BaseIntegration, IntegrationError, RateLimiter, RetryConfig


class ProductHuntConfig:
    """Product Hunt OAuth and API configuration."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        api_url: str = "https://api.producthunt.com/v2/api/graphql",
        auth_url: str = "https://api.producthunt.com/v2/oauth/token",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.api_url = api_url
        self.auth_url = auth_url


class ProductHuntIntegration(BaseIntegration):
    """Product Hunt integration using GraphQL API v2."""

    PLATFORM = "product_hunt"

    def __init__(self, config: ProductHuntConfig, retry_config: Optional[RetryConfig] = None):
        super().__init__(retry_config=retry_config)
        self.config = config
        self.access_token: Optional[str] = None
        self.refresh_token_value: Optional[str] = None
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

    async def _make_request(
        self,
        query: str,
        variables: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict:
        """Make a GraphQL request to Product Hunt API."""
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.access_token:
            request_headers["Authorization"] = f"Bearer {self.access_token}"
        if headers:
            request_headers.update(headers)

        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.api_url,
                json=payload,
                headers=request_headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, content: dict) -> dict:
        """Create a Product Hunt launch/post."""
        query = """
        mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                post {
                    id
                    name
                    tagline
                    url
                    votesCount
                    commentsCount
                    createdAt
                }
            }
        }
        """
        variables = {
            "input": {
                "name": content.get("name"),
                "tagline": content.get("tagline"),
                "description": content.get("description"),
                "url": content.get("url"),
                "topics": content.get("topics", []),
            }
        }

        result = await self._make_request(query, variables)

        if "errors" in result:
            errors = result["errors"]
            error_msg = "; ".join(e.get("message", "Unknown error") for e in errors)
            raise IntegrationError(f"Product Hunt GraphQL error: {error_msg}")

        post_data = result.get("data", {}).get("createPost", {}).get("post", {})
        if not post_data:
            raise IntegrationError("Product Hunt: no post data in response")

        return {
            "id": post_data.get("id"),
            "name": post_data.get("name"),
            "tagline": post_data.get("tagline"),
            "url": post_data.get("url"),
            "votes_count": post_data.get("votesCount", 0),
            "comments_count": post_data.get("commentsCount", 0),
            "created_at": post_data.get("createdAt"),
            "platform": self.PLATFORM,
        }

    async def health_check(self) -> dict:
        """Check Product Hunt API connectivity."""
        try:
            query = "{ user { id } }"
            result = await self._make_request(query)
            if "data" in result:
                return {"status": "healthy", "platform": self.PLATFORM}
            return {
                "status": "unhealthy",
                "platform": self.PLATFORM,
                "error": "No data in response",
            }
        except Exception as e:
            return {"status": "unhealthy", "platform": self.PLATFORM, "error": str(e)}

    async def exchange_code(self, code: str) -> dict:
        """Exchange OAuth authorization code for access token."""
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        self.access_token = data.get("access_token")
        self.refresh_token_value = data.get("refresh_token")
        return data

    async def refresh_access_token(self, refresh_token: Optional[str] = None) -> dict:
        """Refresh the OAuth access token."""
        token = refresh_token or self.refresh_token_value
        if not token:
            raise IntegrationError("No refresh token available")

        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        self.access_token = data.get("access_token")
        if data.get("refresh_token"):
            self.refresh_token_value = data["refresh_token"]
        return data
