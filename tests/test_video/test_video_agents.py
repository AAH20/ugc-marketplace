"""Tests for Video Generation agents."""

from __future__ import annotations

import uuid

import pytest

from ugc_marketplace.video.agents.quality_assessor import VideoQualityAssessorAgent
from ugc_marketplace.video.agents.renderer import VideoRendererAgent
from ugc_marketplace.video.agents.scriptwriter import VideoScriptwriterAgent
from ugc_marketplace.video.models import (
    VideoAspectRatio,
    VideoFormat,
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoProvider,
    VideoStatus,
)


class TestVideoScriptwriterAgent:
    """Tests for VideoScriptwriterAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that scriptwriter returns success."""
        agent = VideoScriptwriterAgent()
        request = VideoGenerationRequest(
            prompt="A 15-second product demo for an AI writing tool",
            duration_seconds=15.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert result.data is not None
        assert "script" in result.data
        assert "scenes" in result.data
        assert "visual_directions" in result.data

    @pytest.mark.asyncio
    async def test_script_has_scenes(self) -> None:
        """Test that generated script has scenes."""
        agent = VideoScriptwriterAgent()
        request = VideoGenerationRequest(
            prompt="Product demo",
            duration_seconds=30.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert len(result.data["scenes"]) >= 3

    @pytest.mark.asyncio
    async def test_scene_timing(self) -> None:
        """Test that scene timing is correct."""
        agent = VideoScriptwriterAgent()
        request = VideoGenerationRequest(
            prompt="Product demo",
            duration_seconds=20.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        scenes = result.data["scenes"]
        # First scene should start at 0
        assert scenes[0]["start_time"] == 0.0
        # Last scene should end at duration
        assert scenes[-1]["end_time"] == 20.0


class TestVideoRendererAgent:
    """Tests for VideoRendererAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that renderer returns success."""
        agent = VideoRendererAgent()
        request = VideoGenerationRequest(
            prompt="Test video",
            provider=VideoProvider.HYPERFRAMES,
            duration_seconds=10.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert result.data is not None
        assert "result" in result.data
        assert "provider_used" in result.data

    @pytest.mark.asyncio
    async def test_hyperframes_rendering(self) -> None:
        """Test HyperFrames rendering path."""
        agent = VideoRendererAgent()
        request = VideoGenerationRequest(
            prompt="Test video",
            provider=VideoProvider.HYPERFRAMES,
            duration_seconds=10.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert result.data["provider_used"] == "hyperframes"

    @pytest.mark.asyncio
    async def test_remotion_rendering(self) -> None:
        """Test Remotion rendering path."""
        agent = VideoRendererAgent()
        request = VideoGenerationRequest(
            prompt="Test video",
            provider=VideoProvider.REMOTION,
            duration_seconds=10.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert result.data["provider_used"] == "remotion"

    @pytest.mark.asyncio
    async def test_auto_provider_selection(self) -> None:
        """Test automatic provider selection."""
        agent = VideoRendererAgent()
        request = VideoGenerationRequest(
            prompt="Test video",
            provider=VideoProvider.NONE,
            duration_seconds=10.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        # Should auto-select HyperFrames as default
        assert result.data["provider_used"] == "hyperframes"

    @pytest.mark.asyncio
    async def test_vertical_video_selects_hyperframes(self) -> None:
        """Test that vertical video selects HyperFrames."""
        agent = VideoRendererAgent()
        request = VideoGenerationRequest(
            prompt="Test video",
            provider=VideoProvider.NONE,
            aspect_ratio=VideoAspectRatio.PORTRAIT,
            duration_seconds=10.0,
        )
        result = await agent.execute(request)
        assert result.success is True
        assert result.data["provider_used"] == "hyperframes"


class TestVideoQualityAssessorAgent:
    """Tests for VideoQualityAssessorAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that assessor returns success."""
        agent = VideoQualityAssessorAgent()
        video = VideoGenerationResult(
            provider=VideoProvider.HYPERFRAMES,
            status=VideoStatus.COMPLETED,
            duration_seconds=15.0,
        )
        result = await agent.execute(video)
        assert result.success is True
        assert result.data is not None
        assert "quality_metrics" in result.data
        assert "engagement_prediction" in result.data
        assert "recommendations" in result.data

    @pytest.mark.asyncio
    async def test_quality_metrics_calculated(self) -> None:
        """Test that quality metrics are calculated."""
        agent = VideoQualityAssessorAgent()
        video = VideoGenerationResult(
            provider=VideoProvider.HYPERFRAMES,
            status=VideoStatus.COMPLETED,
            duration_seconds=15.0,
        )
        result = await agent.execute(video)
        assert result.success is True
        metrics = result.data["quality_metrics"]
        assert 0 <= metrics["visual_quality"] <= 1
        assert 0 <= metrics["audio_quality"] <= 1
        assert 0 <= metrics["overall_score"] <= 1

    @pytest.mark.asyncio
    async def test_hyperframes_higher_quality(self) -> None:
        """Test that HyperFrames gets higher quality score."""
        agent = VideoQualityAssessorAgent()
        video = VideoGenerationResult(
            provider=VideoProvider.HYPERFRAMES,
            status=VideoStatus.COMPLETED,
            duration_seconds=15.0,
        )
        result = await agent.execute(video)
        assert result.success is True
        assert result.data["quality_metrics"]["visual_quality"] >= 0.8

    @pytest.mark.asyncio
    async def test_recommendations_generated(self) -> None:
        """Test that recommendations are generated."""
        agent = VideoQualityAssessorAgent()
        video = VideoGenerationResult(
            provider=VideoProvider.HYPERFRAMES,
            status=VideoStatus.COMPLETED,
            duration_seconds=15.0,
        )
        result = await agent.execute(video)
        assert result.success is True
        assert len(result.data["recommendations"]) > 0
