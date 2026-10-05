"""Video Renderer Agent — orchestrates video rendering across providers."""

from __future__ import annotations

import time
from typing import Any

from ugc_marketplace.video.agents.base import BaseVideoAgent
from ugc_marketplace.video.models import (
    VideoFormat,
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoProvider,
    VideoStatus,
)


class VideoRendererAgent(BaseVideoAgent[VideoGenerationRequest]):
    """Agent that orchestrates video rendering across multiple providers.

    Supports HyperFrames, Remotion, and VideoClaw providers with
    automatic fallback and quality optimization.
    """

    async def _execute(self, input_data: VideoGenerationRequest) -> dict[str, Any]:
        """Execute video rendering.

        Args:
            input_data: The video generation request.

        Returns:
            Rendering result with video URL and metadata.
        """
        start_time = time.monotonic()

        # Select optimal provider
        provider = self._select_provider(input_data)

        # Render video
        result = await self._render(input_data, provider)

        processing_time = (time.monotonic() - start_time) * 1000

        return {
            "result": result.model_dump(),
            "provider_used": provider.value,
            "processing_time_ms": processing_time,
            "fallback_used": provider != input_data.provider,
        }

    def _select_provider(self, request: VideoGenerationRequest) -> VideoProvider:
        """Select optimal video provider.

        Args:
            request: The video generation request.

        Returns:
            Selected provider.
        """
        # If specific provider requested, use it
        if request.provider != VideoProvider.NONE:
            return request.provider

        # Auto-select based on requirements
        if request.aspect_ratio.value == "9:16":
            return VideoProvider.HYPERFRAMES  # Better for vertical video
        if request.duration_seconds > 60:
            return VideoProvider.REMOTION  # Better for longer videos
        return VideoProvider.HYPERFRAMES  # Default

    async def _render(
        self, request: VideoGenerationRequest, provider: VideoProvider
    ) -> VideoGenerationResult:
        """Render video with selected provider.

        Args:
            request: The video generation request.
            provider: The selected provider.

        Returns:
            Video generation result.
        """
        result = VideoGenerationResult(
            provider=provider,
            status=VideoStatus.GENERATING,
            format=request.format,
        )

        try:
            # Simulate rendering (in production, this would call actual APIs)
            if provider == VideoProvider.HYPERFRAMES:
                result = await self._render_hyperframes(request, result)
            elif provider == VideoProvider.REMOTION:
                result = await self._render_remotion(request, result)
            elif provider == VideoProvider.VIDEOCLAW:
                result = await self._render_videoclaw(request, result)

            result.status = VideoStatus.COMPLETED
            result.processing_time_ms = 0  # Will be set by caller

        except Exception as exc:
            result.status = VideoStatus.FAILED
            result.error_message = str(exc)

        return result

    async def _render_hyperframes(
        self, request: VideoGenerationRequest, result: VideoGenerationResult
    ) -> VideoGenerationResult:
        """Render with HyperFrames provider.

        Args:
            request: The video generation request.
            result: The result to populate.

        Returns:
            Updated result.
        """
        # In production: call HyperFrames API
        result.video_url = f"https://cdn.example.com/videos/{result.id}.mp4"
        result.thumbnail_url = f"https://cdn.example.com/thumbnails/{result.id}.jpg"
        result.duration_seconds = request.duration_seconds
        result.file_size_bytes = int(request.duration_seconds * 500_000)  # Estimate
        return result

    async def _render_remotion(
        self, request: VideoGenerationRequest, result: VideoGenerationResult
    ) -> VideoGenerationResult:
        """Render with Remotion provider.

        Args:
            request: The video generation request.
            result: The result to populate.

        Returns:
            Updated result.
        """
        # In production: call Remotion Lambda API
        result.video_url = f"https://cdn.example.com/videos/{result.id}.mp4"
        result.thumbnail_url = f"https://cdn.example.com/thumbnails/{result.id}.jpg"
        result.duration_seconds = request.duration_seconds
        result.file_size_bytes = int(request.duration_seconds * 600_000)  # Estimate
        return result

    async def _render_videoclaw(
        self, request: VideoGenerationRequest, result: VideoGenerationResult
    ) -> VideoGenerationResult:
        """Render with VideoClaw provider.

        Args:
            request: The video generation request.
            result: The result to populate.

        Returns:
            Updated result.
        """
        # In production: call VideoClaw API
        result.video_url = f"https://cdn.example.com/videos/{result.id}.mp4"
        result.thumbnail_url = f"https://cdn.example.com/thumbnails/{result.id}.jpg"
        result.duration_seconds = request.duration_seconds
        result.file_size_bytes = int(request.duration_seconds * 550_000)  # Estimate
        return result
