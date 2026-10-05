"""Tests for Video Generation models."""

from __future__ import annotations

import uuid

import pytest

from ugc_marketplace.video.models import (
    BatchVideoRequest,
    BatchVideoResult,
    VideoAspectRatio,
    VideoFormat,
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoProvider,
    VideoQualityMetrics,
    VideoStatus,
    VideoTemplate,
)


class TestVideoGenerationRequest:
    """Tests for VideoGenerationRequest model."""

    def test_minimal_request(self) -> None:
        """Test minimal video generation request."""
        request = VideoGenerationRequest(prompt="A product demo video")
        assert request.prompt == "A product demo video"
        assert request.provider == VideoProvider.HYPERFRAMES
        assert request.format == VideoFormat.MP4
        assert request.aspect_ratio == VideoAspectRatio.LANDSCAPE
        assert request.duration_seconds == 10.0

    def test_full_request(self) -> None:
        """Test full video generation request."""
        request = VideoGenerationRequest(
            prompt="Launch video for AI product",
            provider=VideoProvider.REMOTION,
            format=VideoFormat.WEBM,
            aspect_ratio=VideoAspectRatio.PORTRAIT,
            duration_seconds=30.0,
            variables={"product_name": "AI Tool", "color": "#00d4ff"},
        )
        assert request.provider == VideoProvider.REMOTION
        assert request.aspect_ratio == VideoAspectRatio.PORTRAIT
        assert request.variables["product_name"] == "AI Tool"

    def test_empty_prompt_rejected(self) -> None:
        """Test that empty prompt is rejected."""
        with pytest.raises(ValueError, match="at least 1 character"):
            VideoGenerationRequest(prompt="")

    def test_duration_bounds(self) -> None:
        """Test that duration must be positive."""
        with pytest.raises(ValueError, match="greater than 0"):
            VideoGenerationRequest(prompt="Test", duration_seconds=0)


class TestVideoGenerationResult:
    """Tests for VideoGenerationResult model."""

    def test_result_defaults(self) -> None:
        """Test result default values."""
        result = VideoGenerationResult(provider=VideoProvider.HYPERFRAMES)
        assert result.status == VideoStatus.PENDING
        assert result.video_url is None
        assert result.id is not None

    def test_completed_result(self) -> None:
        """Test completed result."""
        result = VideoGenerationResult(
            provider=VideoProvider.HYPERFRAMES,
            status=VideoStatus.COMPLETED,
            video_url="https://cdn.example.com/video.mp4",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            duration_seconds=15.0,
            file_size_bytes=7500000,
        )
        assert result.status == VideoStatus.COMPLETED
        assert result.video_url is not None


class TestVideoQualityMetrics:
    """Tests for VideoQualityMetrics model."""

    def test_quality_metrics(self) -> None:
        """Test quality metrics model."""
        metrics = VideoQualityMetrics(
            video_id=uuid.uuid4(),
            visual_quality=0.85,
            audio_quality=0.75,
            pacing_score=0.9,
            engagement_prediction=0.8,
            brand_consistency=0.7,
            overall_score=0.8,
        )
        assert metrics.overall_score == 0.8
        assert metrics.issues == []

    def test_quality_metrics_with_issues(self) -> None:
        """Test quality metrics with issues."""
        metrics = VideoQualityMetrics(
            video_id=uuid.uuid4(),
            visual_quality=0.5,
            audio_quality=0.6,
            pacing_score=0.4,
            engagement_prediction=0.5,
            brand_consistency=0.5,
            overall_score=0.5,
            issues=["Low visual quality", "Poor pacing"],
        )
        assert len(metrics.issues) == 2


class TestVideoTemplate:
    """Tests for VideoTemplate model."""

    def test_template_creation(self) -> None:
        """Test video template creation."""
        template = VideoTemplate(
            name="Launch Video",
            description="Product launch template",
            html_template="<html><body>Launch</body></html>",
            variables={"product_name": "My Product"},
        )
        assert template.name == "Launch Video"
        assert template.aspect_ratio == VideoAspectRatio.LANDSCAPE
        assert template.duration_seconds == 10.0


class TestBatchVideoRequest:
    """Tests for BatchVideoRequest model."""

    def test_batch_request(self) -> None:
        """Test batch video request."""
        request = BatchVideoRequest(
            requests=[
                VideoGenerationRequest(prompt="Video 1"),
                VideoGenerationRequest(prompt="Video 2"),
            ]
        )
        assert len(request.requests) == 2
        assert request.priority == "normal"

    def test_empty_batch_rejected(self) -> None:
        """Test that empty batch is rejected."""
        with pytest.raises(ValueError, match="at least 1 item"):
            BatchVideoRequest(requests=[])
