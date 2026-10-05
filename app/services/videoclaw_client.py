"""VideoClaw API client."""

from typing import Optional
import httpx
from app.integrations.base import BaseIntegration, IntegrationError, RateLimiter, RetryConfig


class VideoClawConfig:
    """VideoClaw API configuration."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.videoclaw.io/v1",
    ):
        self.api_key = api_key
        self.base_url = base_url


class VideoClawClient(BaseIntegration):
    """Client for VideoClaw video processing API."""

    PLATFORM = "videoclaw"

    def __init__(self, config: VideoClawConfig, retry_config: Optional[RetryConfig] = None):
        super().__init__(retry_config=retry_config)
        self.config = config
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated request to VideoClaw API."""
        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, content: dict) -> dict:
        """Create a new video processing job."""
        result = await self._make_request("POST", "/jobs", data=content)
        return {
            "job_id": result.get("id"),
            "status": result.get("status", "pending"),
            "platform": self.PLATFORM,
        }

    async def health_check(self) -> dict:
        """Check VideoClaw API connectivity."""
        try:
            result = await self._make_request("GET", "/health")
            return {"status": "healthy", "platform": self.PLATFORM}
        except Exception as e:
            return {"status": "unhealthy", "platform": self.PLATFORM, "error": str(e)}

    async def get_job_status(self, job_id: str) -> dict:
        """Get the status of a processing job."""
        return await self._make_request("GET", f"/jobs/{job_id}")

    async def cancel_job(self, job_id: str) -> dict:
        """Cancel a processing job."""
        return await self._make_request("POST", f"/jobs/{job_id}/cancel")
