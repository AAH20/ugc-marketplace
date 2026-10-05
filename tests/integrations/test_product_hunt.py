"""Tests for Product Hunt integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app import models  # noqa: F401
from app.integrations.product_hunt import ProductHuntIntegration, ProductHuntConfig


class TestProductHuntConfig:
    """Test Product Hunt configuration."""

    def test_config_stores_credentials(self):
        config = ProductHuntConfig(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.redirect_uri == "http://localhost:8000/callback"

    def test_config_default_api_url(self):
        config = ProductHuntConfig(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        assert config.api_url == "https://api.producthunt.com/v2/api/graphql"


class TestProductHuntIntegration:
    """Test Product Hunt integration."""

    @pytest.fixture
    def config(self):
        return ProductHuntConfig(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )

    @pytest.fixture
    def integration(self, config):
        return ProductHuntIntegration(config)

    @pytest.mark.asyncio
    async def test_health_check_success(self, integration):
        """Health check returns healthy when API is reachable."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"user": {"id": "123"}}}
            result = await integration.health_check()
            assert result["status"] == "healthy"
            assert result["platform"] == "product_hunt"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, integration):
        """Health check returns unhealthy when API fails."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("API down")
            result = await integration.health_check()
            assert result["status"] == "unhealthy"
            assert result["platform"] == "product_hunt"

    @pytest.mark.asyncio
    async def test_post_creates_launch(self, integration):
        """Post creates a Product Hunt launch."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "data": {
                    "createPost": {
                        "post": {"id": "ph_123", "name": "Test Product"}
                    }
                }
            }
            result = await integration.post({
                "name": "Test Product",
                "tagline": "A test product",
                "description": "Full description here",
                "url": "https://example.com",
            })
            assert result["id"] == "ph_123"
            assert result["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_post_handles_graphql_errors(self, integration):
        """Post raises IntegrationError on GraphQL errors."""
        with patch.object(integration, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "errors": [{"message": "Validation failed"}]
            }
            with pytest.raises(Exception):
                await integration.post({"name": "Test"})

    @pytest.mark.asyncio
    async def test_oauth_token_exchange(self, integration):
        """OAuth code exchange returns access token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.product_hunt.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await integration.exchange_code("auth_code_123")
            assert result["access_token"] == "token_123"

    @pytest.mark.asyncio
    async def test_oauth_refresh_token(self, integration):
        """Token refresh returns new access token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_token_456",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.product_hunt.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await integration.refresh_access_token("refresh_token_123")
            assert result["access_token"] == "new_token_456"

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, integration):
        """Rate limiter is applied to requests."""
        assert integration.rate_limiter is not None
        assert integration.rate_limiter.max_requests > 0

    @pytest.mark.asyncio
    async def test_post_includes_auth_header(self, integration):
        """Authenticated requests include Bearer token."""
        integration.access_token = "test_token"
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"createPost": {"post": {"id": "123"}}}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.product_hunt.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await integration.post({"name": "Test"})
            call_kwargs = mock_client.return_value.__aenter__.return_value.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test_token"
