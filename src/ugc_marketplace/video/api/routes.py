"""Video Generation API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from ugc_marketplace.video.agents.quality_assessor import VideoQualityAssessorAgent
from ugc_marketplace.video.agents.renderer import VideoRendererAgent
from ugc_marketplace.video.agents.scriptwriter import VideoScriptwriterAgent
from ugc_marketplace.video.models import (
    BatchVideoRequest,
    BatchVideoResult,
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoProvider,
    VideoStatus,
)

router = APIRouter()

# In-memory store for demo (replace with DB in production)
_videos: dict[uuid.UUID, VideoGenerationResult] = {}


@router.post("/generate", response_model=VideoGenerationResult, status_code=status.HTTP_201_CREATED)
async def generate_video(request: VideoGenerationRequest) -> VideoGenerationResult:
    """Generate a video from a prompt."""
    # First generate script
    scriptwriter = VideoScriptwriterAgent()
    script_result = await scriptwriter.execute(request)

    if not script_result.success:
        raise HTTPException(status_code=500, detail="Script generation failed")

    # Then render video
    renderer = VideoRendererAgent()
    result = await renderer.execute(request)

    if not result.success or result.data is None:
        raise HTTPException(status_code=500, detail=result.error or "Video generation failed")

    # Build video result from renderer output
    renderer_output = result.data
    inner = renderer_output.get("result", {})
    video_result = VideoGenerationResult(
        provider=inner.get("provider", request.provider),
        status=inner.get("status", VideoStatus.FAILED),
        video_url=inner.get("video_url"),
        thumbnail_url=inner.get("thumbnail_url"),
        duration_seconds=inner.get("duration_seconds", request.duration_seconds),
        file_size_bytes=inner.get("file_size_bytes", 0),
        format=inner.get("format", request.format),
    )
    _videos[video_result.id] = video_result

    return video_result


@router.get("/{video_id}", response_model=VideoGenerationResult)
async def get_video(video_id: uuid.UUID) -> VideoGenerationResult:
    """Get a video generation result by ID."""
    if video_id not in _videos:
        raise HTTPException(status_code=404, detail="Video not found")
    return _videos[video_id]


@router.post("/{video_id}/assess")
async def assess_video(video_id: uuid.UUID) -> dict:
    """Assess video quality."""
    if video_id not in _videos:
        raise HTTPException(status_code=404, detail="Video not found")

    video = _videos[video_id]
    assessor = VideoQualityAssessorAgent()
    result = await assessor.execute(video)

    if not result.success or result.data is None:
        raise HTTPException(status_code=500, detail=result.error or "Assessment failed")

    return result.data


@router.post("/batch", response_model=BatchVideoResult)
async def batch_generate(request: BatchVideoRequest) -> BatchVideoResult:
    """Generate multiple videos in batch."""
    renderer = VideoRendererAgent()
    results: list[VideoGenerationResult] = []

    for req in request.requests:
        result = await renderer.execute(req)
        if result.success and result.data is not None:
            inner = result.data.get("result", {})
            video_result = VideoGenerationResult(
                provider=inner.get("provider", req.provider),
                status=inner.get("status", VideoStatus.FAILED),
                video_url=inner.get("video_url"),
                thumbnail_url=inner.get("thumbnail_url"),
                duration_seconds=inner.get("duration_seconds", req.duration_seconds),
                file_size_bytes=inner.get("file_size_bytes", 0),
                format=inner.get("format", req.format),
            )
            _videos[video_result.id] = video_result
            results.append(video_result)

    return BatchVideoResult(
        results=results,
        total_requested=len(request.requests),
        total_completed=len([r for r in results if r.status.value == "completed"]),
        total_failed=len([r for r in results if r.status.value == "failed"]),
    )


@router.get("/providers")
async def list_providers() -> list[str]:
    """List all supported video providers."""
    return [p.value for p in VideoProvider if p != VideoProvider.NONE]
