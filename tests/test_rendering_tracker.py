"""Integration tests for rendering status tracking and cost calculation."""
import pytest
from app.services.rendering_tracker import RenderCostCalculator, RenderTracker


class TestRenderCostCalculator:
    """Tests for render cost calculation based on pricing tiers."""

    def test_calculate_cost_1080p30(self):
        """Cost for 1080p30: $0.10/min."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=120, resolution="1080p", fps=30)
        assert cost == pytest.approx(0.20)

    def test_calculate_cost_1080p60(self):
        """Cost for 1080p60: $0.20/min."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=120, resolution="1080p", fps=60)
        assert cost == pytest.approx(0.40)

    def test_calculate_cost_720p30(self):
        """Cost for 720p30 uses base rate."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=60, resolution="720p", fps=30)
        assert cost == pytest.approx(0.10)

    def test_calculate_cost_4k60(self):
        """Cost for 4K60 uses premium rate."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=60, resolution="4k", fps=60)
        assert cost == pytest.approx(0.40)

    def test_calculate_cost_fractional_minutes(self):
        """Cost rounds up to nearest minute."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=90, resolution="1080p", fps=30)
        assert cost == pytest.approx(0.20)

    def test_calculate_cost_zero_duration(self):
        """Zero duration has zero cost."""
        calc = RenderCostCalculator()
        cost = calc.calculate_cost(duration_seconds=0, resolution="1080p", fps=30)
        assert cost == 0.0

    def test_calculate_cost_batch(self):
        """Calculate total cost for batch render."""
        calc = RenderCostCalculator()
        durations = [60, 120, 90]
        total = calc.calculate_batch_cost(durations, resolution="1080p", fps=30)
        assert total == pytest.approx(0.50)

    def test_get_rate_1080p30(self):
        """Get rate for 1080p30."""
        calc = RenderCostCalculator()
        rate = calc.get_rate(resolution="1080p", fps=30)
        assert rate == 0.10

    def test_get_rate_1080p60(self):
        """Get rate for 1080p60."""
        calc = RenderCostCalculator()
        rate = calc.get_rate(resolution="1080p", fps=60)
        assert rate == 0.20

    def test_get_rate_default(self):
        """Default rate for unknown quality."""
        calc = RenderCostCalculator()
        rate = calc.get_rate(resolution="unknown", fps=30)
        assert rate == 0.10


class TestRenderTracker:
    """Tests for render status tracking."""

    @pytest.fixture
    def tracker(self):
        return RenderTracker()

    def test_track_new_render(self, tracker):
        """Start tracking a new render."""
        entry = tracker.track_render(
            render_id="render_001",
            asset_id="asset_001",
            variables={"title": "Test"},
            resolution="1080p",
            fps=30,
        )
        assert entry.render_id == "render_001"
        assert entry.status == "queued"
        assert entry.resolution == "1080p"
        assert entry.fps == 30

    def test_update_render_status(self, tracker):
        """Update render status."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.update_status("render_001", "rendering", progress=50)
        entry = tracker.get_render("render_001")
        assert entry.status == "rendering"
        assert entry.progress == 50

    def test_update_render_complete(self, tracker):
        """Mark render as complete with output URL."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.update_status(
            "render_001", "complete", progress=100,
            output_url="https://cdn.hyperframes.io/renders/render_001.mp4",
            duration_seconds=120,
        )
        entry = tracker.get_render("render_001")
        assert entry.status == "complete"
        assert entry.output_url == "https://cdn.hyperframes.io/renders/render_001.mp4"
        assert entry.duration_seconds == 120

    def test_update_render_failed(self, tracker):
        """Mark render as failed with error message."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.update_status("render_001", "failed", error="Rendering engine crashed")
        entry = tracker.get_render("render_001")
        assert entry.status == "failed"
        assert entry.error == "Rendering engine crashed"

    def test_get_render_not_found(self, tracker):
        """Return None for unknown render ID."""
        assert tracker.get_render("nonexistent") is None

    def test_list_renders(self, tracker):
        """List all tracked renders."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.track_render("render_002", "asset_002", {}, "1080p", 60)
        tracker.track_render("render_003", "asset_003", {}, "720p", 30)
        assert len(tracker.list_renders()) == 3

    def test_list_renders_by_status(self, tracker):
        """Filter renders by status."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.track_render("render_002", "asset_002", {}, "1080p", 60)
        tracker.update_status("render_001", "complete", progress=100)
        complete = tracker.list_renders(status="complete")
        assert len(complete) == 1
        assert complete[0].render_id == "render_001"

    def test_get_render_cost(self, tracker):
        """Get calculated cost for a completed render."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.update_status("render_001", "complete", progress=100, duration_seconds=120)
        cost = tracker.get_render_cost("render_001")
        assert cost == pytest.approx(0.20)

    def test_get_total_cost(self, tracker):
        """Get total cost across all completed renders."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.track_render("render_002", "asset_002", {}, "1080p", 60)
        tracker.update_status("render_001", "complete", progress=100, duration_seconds=60)
        tracker.update_status("render_002", "complete", progress=100, duration_seconds=60)
        total = tracker.get_total_cost()
        assert total == pytest.approx(0.30)

    def test_remove_render(self, tracker):
        """Remove a render from tracking."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.remove_render("render_001")
        assert tracker.get_render("render_001") is None

    def test_clear_completed(self, tracker):
        """Clear all completed renders from tracking."""
        tracker.track_render("render_001", "asset_001", {}, "1080p", 30)
        tracker.track_render("render_002", "asset_002", {}, "1080p", 60)
        tracker.update_status("render_001", "complete", progress=100)
        tracker.clear_completed()
        renders = tracker.list_renders()
        assert len(renders) == 1
        assert renders[0].render_id == "render_002"
