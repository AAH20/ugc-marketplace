"""Integration tests for HyperFrames API client with mocked HTTP."""
import json
import zipfile

import httpx
import pytest
from pytest_httpx import HTTPXMock

from app import models  # noqa: F401
from app.services.hyperframes_client import (
    HyperFramesClient,
    HyperFramesError,
)

BASE_URL = "https://api.hyperframes.io"
API_KEY = "hf_test_key_12345"


@pytest.fixture
def client():
    return HyperFramesClient(api_key=API_KEY, base_url=BASE_URL)


@pytest.fixture
def sample_zip(tmp_path):
    """Create a sample zip file for upload tests."""
    zip_path = tmp_path / "test_asset.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("scene.tsx", "export const Scene = () => <div>Test</div>;")
        zf.writestr("data.json", json.dumps({"title": "Test Video"}))
    return zip_path


class TestHyperFramesClientUpload:
    """Tests for asset upload via POST /v3/assets."""

    def test_upload_asset_success(self, client, sample_zip, httpx_mock: HTTPXMock):
        """Upload a zip file and receive an asset ID."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/assets",
            method="POST",
            status_code=201,
            json={
                "id": "asset_abc123",
                "filename": "test_asset.zip",
                "size_bytes": 1024,
                "status": "ready",
            },
        )

        result = client.upload_asset(str(sample_zip))

        assert result["id"] == "asset_abc123"
        assert result["status"] == "ready"

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        assert b"test_asset.zip" in request.content

    def test_upload_asset_http_error(self, client, sample_zip, httpx_mock: HTTPXMock):
        """Handle HTTP errors during upload."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/assets",
            method="POST",
            status_code=400,
            json={"error": "Invalid zip file format"},
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.upload_asset(str(sample_zip))

        assert "400" in str(exc_info.value)

    def test_upload_asset_network_error(self, client, sample_zip, httpx_mock: HTTPXMock):
        """Handle network errors during upload."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url=f"{BASE_URL}/v3/assets",
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.upload_asset(str(sample_zip))

        assert "Connection refused" in str(exc_info.value)

    def test_upload_asset_not_found(self, client, tmp_path):
        """Raise error when zip file does not exist."""
        with pytest.raises(FileNotFoundError):
            client.upload_asset(str(tmp_path / "nonexistent.zip"))


class TestHyperFramesClientRender:
    """Tests for render submission via POST /v3/hyperframes/renders."""

    def test_submit_render_success(self, client, httpx_mock: HTTPXMock):
        """Submit a render job and receive a render ID."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders",
            method="POST",
            status_code=201,
            json={
                "id": "render_xyz789",
                "asset_id": "asset_abc123",
                "status": "queued",
                "variables": {"title": "My Video"},
                "quality": {"resolution": "1080p", "fps": 30},
            },
        )

        result = client.submit_render(
            asset_id="asset_abc123",
            variables={"title": "My Video"},
            resolution="1080p",
            fps=30,
        )

        assert result["id"] == "render_xyz789"
        assert result["status"] == "queued"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["asset_id"] == "asset_abc123"
        assert body["variables"] == {"title": "My Video"}
        assert body["quality"]["resolution"] == "1080p"
        assert body["quality"]["fps"] == 30

    def test_submit_render_with_batch_variables(self, client, httpx_mock: HTTPXMock):
        """Submit a render with batch variables for multiple outputs."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders",
            method="POST",
            status_code=201,
            json={
                "id": "render_batch_001",
                "asset_id": "asset_abc123",
                "status": "queued",
                "batch": True,
                "variables": [{"title": "Video 1"}, {"title": "Video 2"}],
            },
        )

        result = client.submit_render(
            asset_id="asset_abc123",
            variables=[{"title": "Video 1"}, {"title": "Video 2"}],
            resolution="1080p",
            fps=30,
        )

        assert result["id"] == "render_batch_001"
        assert result["batch"] is True

    def test_submit_render_http_error(self, client, httpx_mock: HTTPXMock):
        """Handle HTTP errors during render submission."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders",
            method="POST",
            status_code=422,
            json={"error": "Asset not found"},
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.submit_render(
                asset_id="nonexistent_asset",
                variables={},
                resolution="1080p",
                fps=30,
            )

        assert "422" in str(exc_info.value)


class TestHyperFramesClientPoll:
    """Tests for render status polling via GET /v3/hyperframes/renders/{id}."""

    def test_get_render_status_success(self, client, httpx_mock: HTTPXMock):
        """Get render status by ID."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789",
            method="GET",
            status_code=200,
            json={
                "id": "render_xyz789",
                "status": "rendering",
                "progress": 45,
                "estimated_completion": "2024-01-01T00:01:00Z",
            },
        )

        result = client.get_render_status("render_xyz789")

        assert result["id"] == "render_xyz789"
        assert result["status"] == "rendering"
        assert result["progress"] == 45

    def test_get_render_status_not_found(self, client, httpx_mock: HTTPXMock):
        """Handle 404 when render ID doesn't exist."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/nonexistent",
            method="GET",
            status_code=404,
            json={"error": "Render not found"},
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.get_render_status("nonexistent")

        assert "404" in str(exc_info.value)

    def test_poll_render_until_complete(self, client, httpx_mock: HTTPXMock):
        """Poll render status until completion."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789",
            method="GET",
            status_code=200,
            json={"id": "render_xyz789", "status": "rendering", "progress": 50},
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789",
            method="GET",
            status_code=200,
            json={
                "id": "render_xyz789",
                "status": "complete",
                "progress": 100,
                "output_url": "https://cdn.hyperframes.io/renders/render_xyz789.mp4",
                "duration_seconds": 120,
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("time.sleep", lambda x: None)
            result = client.poll_render("render_xyz789", poll_interval=0.1, max_attempts=5)

        assert result["status"] == "complete"
        assert result["progress"] == 100
        assert result["output_url"] == "https://cdn.hyperframes.io/renders/render_xyz789.mp4"

    def test_poll_render_timeout(self, client, httpx_mock: HTTPXMock):
        """Raise timeout error when render doesn't complete in time."""
        for _ in range(3):
            httpx_mock.add_response(
                url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789",
                method="GET",
                status_code=200,
                json={"id": "render_xyz789", "status": "rendering", "progress": 10},
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("time.sleep", lambda x: None)
            with pytest.raises(HyperFramesError) as exc_info:
                client.poll_render("render_xyz789", poll_interval=0.1, max_attempts=3)

        assert "timeout" in str(exc_info.value).lower() or "max_attempts" in str(exc_info.value).lower()

    def test_poll_render_failed_status(self, client, httpx_mock: HTTPXMock):
        """Raise error when render fails."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789",
            method="GET",
            status_code=200,
            json={
                "id": "render_xyz789",
                "status": "failed",
                "error": "Rendering engine crashed",
            },
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.poll_render("render_xyz789", poll_interval=0.1, max_attempts=5)

        assert "failed" in str(exc_info.value).lower()


class TestHyperFramesClientDownload:
    """Tests for render download."""

    def test_download_render_success(self, client, httpx_mock: HTTPXMock, tmp_path):
        """Download a rendered video file."""
        video_content = b"fake video data" * 1000
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789/download",
            method="GET",
            status_code=200,
            content=video_content,
        )

        output_path = tmp_path / "output.mp4"
        client.download_render("render_xyz789", str(output_path))

        assert output_path.exists()
        assert output_path.read_bytes() == video_content

    def test_download_render_not_ready(self, client, httpx_mock: HTTPXMock, tmp_path):
        """Handle download when render is not complete."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_xyz789/download",
            method="GET",
            status_code=409,
            json={"error": "Render not complete"},
        )

        with pytest.raises(HyperFramesError) as exc_info:
            client.download_render("render_xyz789", str(tmp_path / "output.mp4"))

        assert "409" in str(exc_info.value)


class TestHyperFramesClientEndToEnd:
    """End-to-end workflow tests with mocked API."""

    def test_full_render_workflow(self, client, sample_zip, httpx_mock: HTTPXMock, tmp_path):
        """Complete workflow: upload -> submit -> poll -> download."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/assets",
            method="POST",
            status_code=201,
            json={"id": "asset_e2e", "status": "ready"},
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders",
            method="POST",
            status_code=201,
            json={"id": "render_e2e", "status": "queued"},
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_e2e",
            method="GET",
            status_code=200,
            json={"id": "render_e2e", "status": "rendering", "progress": 50},
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_e2e",
            method="GET",
            status_code=200,
            json={
                "id": "render_e2e",
                "status": "complete",
                "progress": 100,
                "output_url": "https://cdn.hyperframes.io/renders/render_e2e.mp4",
                "duration_seconds": 60,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/v3/hyperframes/renders/render_e2e/download",
            method="GET",
            status_code=200,
            content=b"fake rendered video",
        )

        asset = client.upload_asset(str(sample_zip))
        assert asset["id"] == "asset_e2e"

        render = client.submit_render(
            asset_id=asset["id"],
            variables={"title": "E2E Test"},
            resolution="1080p",
            fps=30,
        )
        assert render["id"] == "render_e2e"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("time.sleep", lambda x: None)
            status = client.poll_render(render["id"], poll_interval=0.1, max_attempts=5)
        assert status["status"] == "complete"

        output_path = tmp_path / "rendered.mp4"
        client.download_render(render["id"], str(output_path))
        assert output_path.read_bytes() == b"fake rendered video"

    def test_client_uses_custom_base_url(self, httpx_mock: HTTPXMock):
        """Client respects custom base URL."""
        custom_url = "https://custom.hyperframes.io"
        client = HyperFramesClient(api_key=API_KEY, base_url=custom_url)

        httpx_mock.add_response(
            url=f"{custom_url}/v3/hyperframes/renders/render_123",
            method="GET",
            status_code=200,
            json={"id": "render_123", "status": "complete"},
        )

        result = client.get_render_status("render_123")
        assert result["status"] == "complete"
