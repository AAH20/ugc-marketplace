"""Comprehensive tests for HyperFrames client and rendering tracker."""
import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from app import models  # noqa: F401
from app.services.hyperframes_client import HyperFramesClient, HyperFramesError, RenderStatus
from app.services.rendering_tracker import RenderTracker, RenderCostCalculator, RenderTrackingEntry


class TestHyperFramesError:
    """Tests for HyperFramesError exception."""

    def test_error_with_message(self):
        """Error with just a message."""
        err = HyperFramesError("test error")
        assert str(err) == "test error"
        assert err.status_code is None

    def test_error_with_status_code(self):
        """Error with status code."""
        err = HyperFramesError("not found", status_code=404)
        assert str(err) == "not found"
        assert err.status_code == 404

    def test_error_is_exception(self):
        """HyperFramesError is an Exception."""
        err = HyperFramesError("test")
        assert isinstance(err, Exception)


class TestRenderStatus:
    """Tests for RenderStatus constants."""

    def test_status_values(self):
        """All status constants have correct values."""
        assert RenderStatus.QUEUED == "queued"
        assert RenderStatus.RENDERING == "rendering"
        assert RenderStatus.COMPLETE == "complete"
        assert RenderStatus.FAILED == "failed"


class TestHyperFramesClient:
    """Tests for HyperFramesClient."""

    def test_client_initialization(self):
        """Client initializes with correct config."""
        client = HyperFramesClient("test-api-key")
        assert client.api_key == "test-api-key"
        assert client.base_url == "https://api.hyperframes.io"
        assert client.timeout == 30.0

    def test_client_custom_base_url(self):
        """Client accepts custom base URL."""
        client = HyperFramesClient("key", base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"

    def test_client_custom_timeout(self):
        """Client accepts custom timeout."""
        client = HyperFramesClient("key", timeout=60.0)
        assert client.timeout == 60.0

    def test_client_context_manager(self):
        """Client works as context manager."""
        with HyperFramesClient("key") as client:
            assert client.api_key == "key"

    def test_upload_asset_file_not_found(self):
        """Upload raises FileNotFoundError for missing file."""
        client = HyperFramesClient("key")
        with pytest.raises(FileNotFoundError):
            client.upload_asset("/nonexistent/file.zip")

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_upload_asset_success(self, mock_client_class):
        """Upload asset returns asset data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "asset_123",
            "filename": "test.zip",
            "size_bytes": 1024,
            "status": "ready",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            client = HyperFramesClient("key")
            result = client.upload_asset(temp_path)
            assert result["id"] == "asset_123"
            assert result["status"] == "ready"
        finally:
            os.unlink(temp_path)

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_submit_render_success(self, mock_client_class):
        """Submit render returns render data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "render_123",
            "status": "queued",
            "variables": {"title": "Test"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = HyperFramesClient("key")
        result = client.submit_render("asset_123", {"title": "Test"})
        assert result["id"] == "render_123"
        assert result["status"] == "queued"

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_get_render_status(self, mock_client_class):
        """Get render status returns status data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "render_123",
            "status": "rendering",
            "progress": 50,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = HyperFramesClient("key")
        result = client.get_render_status("render_123")
        assert result["status"] == "rendering"
        assert result["progress"] == 50

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_poll_render_complete(self, mock_client_class):
        """Poll render returns when complete."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "render_123",
            "status": "complete",
            "progress": 100,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = HyperFramesClient("key")
        result = client.poll_render("render_123", poll_interval=0.01)
        assert result["status"] == "complete"

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_poll_render_failed(self, mock_client_class):
        """Poll render raises on failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "render_123",
            "status": "failed",
            "error": "Out of memory",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = HyperFramesClient("key")
        with pytest.raises(HyperFramesError, match="Render failed"):
            client.poll_render("render_123", poll_interval=0.01)

    @patch("app.services.hyperframes_client.httpx.Client")
    def test_download_render(self, mock_client_class):
        """Download render saves file."""
        mock_response = MagicMock()
        mock_response.content = b"video data"
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.mp4")
            client = HyperFramesClient("key")
            # Mock get_render_status to return complete
            with patch.object(client, "get_render_status", return_value={"status": "complete"}):
                client.download_render("render_123", output_path)
            assert os.path.exists(output_path)
            with open(output_path, "rb") as f:
                assert f.read() == b"video data"


class TestRenderCostCalculator:
    """Tests for RenderCostCalculator."""

    def test_get_rate_1080p30(self):
        """1080p30 rate is $0.10/min."""
        calc = RenderCostCalculator()
        assert calc.get_rate("1080p", 30) == 0.10

    def test_get_rate_1080p60(self):
        """1080p60 rate is $0.20/min."""
        calc = RenderCostCalculator()
        assert calc.get_rate("1080p", 60) == 0.20

    def test_get_rate_720p30(self):
        """720p30 rate is $0.10/min."""
        calc = RenderCostCalculator()
        assert calc.get_rate("720p", 30) == 0.10

    def test_get_rate_4k30(self):
        """4K30 rate is $0.20/min."""
        calc = RenderCostCalculator()
        assert calc.get_rate("4k", 30) == 0.20

    def test_get_rate_4k60(self):
        """4K60 rate is $0.40/min."""
        calc = RenderCostCalculator()
        assert calc.get_rate("4k", 60) == 0.40

    def test_get_rate_unknown_default(self):
        """Unknown resolution/fps uses default rate."""
        calc = RenderCostCalculator()
        assert calc.get_rate("8k", 120) == 0.10

    def test_calculate_cost_zero_duration(self):
        """Zero duration means zero cost."""
        calc = RenderCostCalculator()
        assert calc.calculate_cost(0) == 0.0

    def test_calculate_cost_negative_duration(self):
        """Negative duration means zero cost."""
        calc = RenderCostCalculator()
        assert calc.calculate_cost(-10) == 0.0

    def test_calculate_cost_one_minute(self):
        """One minute at 1080p30 costs $0.10."""
        calc = RenderCostCalculator()
        assert calc.calculate_cost(60) == 0.10

    def test_calculate_cost_rounds_up(self):
        """Duration rounds up to nearest minute."""
        calc = RenderCostCalculator()
        assert calc.calculate_cost(61) == 0.20

    def test_calculate_cost_1080p60(self):
        """1080p60 costs more than 1080p30."""
        calc = RenderCostCalculator()
        cost_30 = calc.calculate_cost(120, "1080p", 30)
        cost_60 = calc.calculate_cost(120, "1080p", 60)
        assert cost_60 > cost_30

    def test_calculate_batch_cost(self):
        """Batch cost sums individual costs."""
        calc = RenderCostCalculator()
        cost = calc.calculate_batch_cost([60, 120, 180])
        assert abs(cost - (0.10 + 0.20 + 0.30)) < 0.001

    def test_calculate_batch_cost_empty(self):
        """Empty batch costs zero."""
        calc = RenderCostCalculator()
        assert calc.calculate_batch_cost([]) == 0.0


class TestRenderTracker:
    """Tests for RenderTracker."""

    def test_track_render(self):
        """Track a new render."""
        tracker = RenderTracker()
        entry = tracker.track_render("render_1", "asset_1", {"title": "Test"})
        assert entry.render_id == "render_1"
        assert entry.status == "queued"
        assert entry.progress == 0

    def test_update_status(self):
        """Update render status."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        entry = tracker.update_status("render_1", "rendering", progress=50)
        assert entry.status == "rendering"
        assert entry.progress == 50

    def test_update_status_not_found(self):
        """Update status for unknown render returns None."""
        tracker = RenderTracker()
        result = tracker.update_status("unknown", "complete")
        assert result is None

    def test_get_render(self):
        """Get tracked render by ID."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        entry = tracker.get_render("render_1")
        assert entry is not None
        assert entry.render_id == "render_1"

    def test_get_render_not_found(self):
        """Get unknown render returns None."""
        tracker = RenderTracker()
        assert tracker.get_render("unknown") is None

    def test_list_renders(self):
        """List all tracked renders."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        tracker.track_render("render_2", "asset_2", {})
        renders = tracker.list_renders()
        assert len(renders) == 2

    def test_list_renders_filtered(self):
        """List renders filtered by status."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        tracker.track_render("render_2", "asset_2", {})
        tracker.update_status("render_1", "complete")
        renders = tracker.list_renders(status="complete")
        assert len(renders) == 1
        assert renders[0].render_id == "render_1"

    def test_get_render_cost(self):
        """Get cost for completed render."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {}, resolution="1080p", fps=30)
        tracker.update_status("render_1", "complete", duration_seconds=120)
        cost = tracker.get_render_cost("render_1")
        assert cost == 0.20

    def test_get_render_cost_not_complete(self):
        """Get cost for incomplete render returns None."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        assert tracker.get_render_cost("render_1") is None

    def test_get_total_cost(self):
        """Get total cost across all completed renders."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {}, resolution="1080p", fps=30)
        tracker.track_render("render_2", "asset_2", {}, resolution="1080p", fps=30)
        tracker.update_status("render_1", "complete", duration_seconds=60)
        tracker.update_status("render_2", "complete", duration_seconds=120)
        assert tracker.get_total_cost() == 0.30

    def test_remove_render(self):
        """Remove a render from tracking."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        assert tracker.remove_render("render_1") is True
        assert tracker.get_render("render_1") is None

    def test_remove_render_not_found(self):
        """Remove unknown render returns False."""
        tracker = RenderTracker()
        assert tracker.remove_render("unknown") is False

    def test_clear_completed(self):
        """Clear completed renders."""
        tracker = RenderTracker()
        tracker.track_render("render_1", "asset_1", {})
        tracker.track_render("render_2", "asset_2", {})
        tracker.update_status("render_1", "complete")
        removed = tracker.clear_completed()
        assert removed == 1
        assert len(tracker.list_renders()) == 1
