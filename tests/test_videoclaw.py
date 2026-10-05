"""Comprehensive tests for VideoClaw client."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.videoclaw_client import VideoClawClient, VideoClawConfig


class TestVideoClawConfig:
    """Tests for VideoClawConfig."""

    def test_config_initialization(self):
        """Config initializes with required fields."""
        config = VideoClawConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.videoclaw.io/v1"

    def test_config_custom_base_url(self):
        """Config accepts custom base URL."""
        config = VideoClawConfig(api_key="test-key", base_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"


class TestVideoClawClient:
    """Tests for VideoClawClient."""

    def test_client_initialization(self):
        """Client initializes with config."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        assert client.config.api_key == "test-key"
        assert client.rate_limiter is not None

    def test_client_platform(self):
        """Client has correct platform identifier."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        assert client.PLATFORM == "videoclaw"

    @pytest.mark.asyncio
    async def test_post_success(self):
        """Post creates a new job."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"id": "job_123", "status": "pending"}
            result = await client.post({"video_url": "https://example.com/video.mp4"})
            assert result["job_id"] == "job_123"
            assert result["status"] == "pending"
            assert result["platform"] == "videoclaw"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Health check returns healthy status."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"status": "ok"}
            result = await client.health_check()
            assert result["status"] == "healthy"
            assert result["platform"] == "videoclaw"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Health check returns unhealthy on error."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Connection failed")
            result = await client.health_check()
            assert result["status"] == "unhealthy"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_job_status(self):
        """Get job status returns status data."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"id": "job_123", "status": "processing"}
            result = await client.get_job_status("job_123")
            assert result["status"] == "processing"

    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Cancel job returns cancellation data."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"id": "job_123", "status": "cancelled"}
            result = await client.cancel_job("job_123")
            assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_make_request_with_auth(self):
        """Make request includes auth header."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch("app.services.videoclaw_client.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            result = await client._make_request("GET", "/test")
            assert result == {"data": "test"}
            call_kwargs = mock_client.request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_make_request_post_with_data(self):
        """Make request POST includes data."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch("app.services.videoclaw_client.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            await client._make_request("POST", "/test", data={"key": "value"})
            call_kwargs = mock_client.request.call_args[1]
            assert call_kwargs["json"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_make_request_with_params(self):
        """Make request includes query params."""
        config = VideoClawConfig(api_key="test-key")
        client = VideoClawClient(config)
        with patch("app.services.videoclaw_client.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            await client._make_request("GET", "/test", params={"page": 1})
            call_kwargs = mock_client.request.call_args[1]
            assert call_kwargs["params"] == {"page": 1}
