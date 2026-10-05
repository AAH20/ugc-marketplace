"""Rendering status tracking and cost calculation."""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RenderTrackingEntry:
    """Tracked render job."""

    render_id: str
    asset_id: str
    variables: dict[str, Any]
    resolution: str
    fps: int
    status: str = "queued"
    progress: int = 0
    output_url: str | None = None
    duration_seconds: int | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RenderCostCalculator:
    """Calculate render costs based on HyperFrames pricing.

    Pricing:
    - $0.10/min for 1080p30
    - $0.20/min for 1080p60
    """

    # Pricing tiers: (resolution, fps) -> $/min
    RATES: dict[tuple[str, int], float] = {
        ("720p", 30): 0.10,
        ("1080p", 30): 0.10,
        ("1080p", 60): 0.20,
        ("4k", 30): 0.20,
        ("4k", 60): 0.40,
    }
    DEFAULT_RATE = 0.10

    def get_rate(self, resolution: str, fps: int) -> float:
        """Get the per-minute rate for a given quality."""
        return self.RATES.get((resolution.lower(), fps), self.DEFAULT_RATE)

    def calculate_cost(
        self,
        duration_seconds: int,
        resolution: str = "1080p",
        fps: int = 30,
    ) -> float:
        """Calculate render cost.

        Args:
            duration_seconds: Render duration in seconds.
            resolution: Output resolution.
            fps: Frames per second.

        Returns:
            Cost in USD.
        """
        if duration_seconds <= 0:
            return 0.0

        minutes = math.ceil(duration_seconds / 60)
        rate = self.get_rate(resolution, fps)
        return round(minutes * rate, 2)

    def calculate_batch_cost(
        self,
        durations: list[int],
        resolution: str = "1080p",
        fps: int = 30,
    ) -> float:
        """Calculate total cost for a batch of renders.

        Args:
            durations: List of render durations in seconds.
            resolution: Output resolution.
            fps: Frames per second.

        Returns:
            Total cost in USD.
        """
        return round(
            sum(self.calculate_cost(d, resolution, fps) for d in durations),
            2,
        )


class RenderTracker:
    """Track render jobs and their statuses."""

    def __init__(self):
        self._renders: dict[str, RenderTrackingEntry] = {}
        self._cost_calculator = RenderCostCalculator()

    def track_render(
        self,
        render_id: str,
        asset_id: str,
        variables: dict[str, Any],
        resolution: str = "1080p",
        fps: int = 30,
    ) -> RenderTrackingEntry:
        """Start tracking a new render job."""
        entry = RenderTrackingEntry(
            render_id=render_id,
            asset_id=asset_id,
            variables=variables,
            resolution=resolution,
            fps=fps,
        )
        self._renders[render_id] = entry
        return entry

    def update_status(
        self,
        render_id: str,
        status: str,
        progress: int | None = None,
        output_url: str | None = None,
        duration_seconds: int | None = None,
        error: str | None = None,
    ) -> RenderTrackingEntry | None:
        """Update the status of a tracked render."""
        entry = self._renders.get(render_id)
        if entry is None:
            return None

        entry.status = status
        if progress is not None:
            entry.progress = progress
        if output_url is not None:
            entry.output_url = output_url
        if duration_seconds is not None:
            entry.duration_seconds = duration_seconds
        if error is not None:
            entry.error = error
        return entry

    def get_render(self, render_id: str) -> RenderTrackingEntry | None:
        """Get a tracked render by ID."""
        return self._renders.get(render_id)

    def list_renders(self, status: str | None = None) -> list[RenderTrackingEntry]:
        """List all tracked renders, optionally filtered by status."""
        renders = list(self._renders.values())
        if status:
            renders = [r for r in renders if r.status == status]
        return renders

    def get_render_cost(self, render_id: str) -> float | None:
        """Get the calculated cost for a completed render."""
        entry = self._renders.get(render_id)
        if entry is None or entry.duration_seconds is None:
            return None
        return self._cost_calculator.calculate_cost(
            entry.duration_seconds,
            entry.resolution,
            entry.fps,
        )

    def get_total_cost(self) -> float:
        """Get total cost across all completed renders."""
        total = 0.0
        for entry in self._renders.values():
            if entry.status == "complete" and entry.duration_seconds is not None:
                total += self._cost_calculator.calculate_cost(
                    entry.duration_seconds,
                    entry.resolution,
                    entry.fps,
                )
        return round(total, 2)

    def remove_render(self, render_id: str) -> bool:
        """Remove a render from tracking. Returns True if removed."""
        if render_id in self._renders:
            del self._renders[render_id]
            return True
        return False

    def clear_completed(self) -> int:
        """Clear all completed renders. Returns count removed."""
        to_remove = [
            rid for rid, r in self._renders.items() if r.status == "complete"
        ]
        for rid in to_remove:
            del self._renders[rid]
        return len(to_remove)
