"""Comprehensive tests for Remotion client Python wrapper."""
import pytest
from src.remotion_client import RemotionClient, RemotionClientConfig, RenderParams, RenderResult


class TestRemotionClientConfig:
    """Tests for RemotionClientConfig."""

    def test_config_initialization(self):
        """Config initializes with required fields."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
        )
        assert config.region == "us-east-1"
        assert config.functionName == "test-function"
        assert config.serveUrl == "https://test.remotion.dev"
        assert config.credentials is None

    def test_config_with_credentials(self):
        """Config with credentials."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
            credentials={
                "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            },
        )
        assert config.credentials is not None
        assert config.credentials["accessKeyId"] == "AKIAIOSFODNN7EXAMPLE"


class TestRenderParams:
    """Tests for RenderParams."""

    def test_params_minimal(self):
        """Params with minimal required fields."""
        params = RenderParams(
            composition="MyComp",
            inputProps={"title": "Hello"},
        )
        assert params.composition == "MyComp"
        assert params.inputProps == {"title": "Hello"}
        assert params.format is None
        assert params.quality is None

    def test_params_full(self):
        """Params with all fields."""
        params = RenderParams(
            composition="MyComp",
            inputProps={"title": "Hello"},
            format="mp4",
            imageFormat="png",
            quality=90,
            scale=1.5,
            frameRange=(0, 100),
            envVariables={"NODE_ENV": "production"},
            maxRetries=3,
            timeoutInMilliseconds=60000,
        )
        assert params.format == "mp4"
        assert params.quality == 90
        assert params.scale == 1.5
        assert params.frameRange == (0, 100)
        assert params.maxRetries == 3


class TestRenderResult:
    """Tests for RenderResult."""

    def test_result_creation(self):
        """Result with render ID and bucket."""
        result = RenderResult(renderId="render_123", bucketName="my-bucket")
        assert result.renderId == "render_123"
        assert result.bucketName == "my-bucket"


class TestRemotionClient:
    """Tests for RemotionClient."""

    def test_client_initialization(self):
        """Client initializes with config."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
        )
        client = RemotionClient(config)
        assert client.config.region == "us-east-1"
        assert client.config.functionName == "test-function"

    @pytest.mark.asyncio
    async def test_render_not_implemented(self):
        """Render raises NotImplementedError (use TypeScript client for actual rendering)."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
        )
        client = RemotionClient(config)
        with pytest.raises(NotImplementedError):
            await client.render(
                RenderParams(composition="MyComp", inputProps={"title": "Hello"})
            )

    @pytest.mark.asyncio
    async def test_poll_not_implemented(self):
        """Poll raises NotImplementedError."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
        )
        client = RemotionClient(config)
        with pytest.raises(NotImplementedError):
            await client.poll("render_123", "my-bucket")

    @pytest.mark.asyncio
    async def test_download_not_implemented(self):
        """Download raises NotImplementedError."""
        config = RemotionClientConfig(
            region="us-east-1",
            functionName="test-function",
            serveUrl="https://test.remotion.dev",
        )
        client = RemotionClient(config)
        with pytest.raises(NotImplementedError):
            await client.download("render_123", "my-bucket", "/tmp/output.mp4")
