"""Video Generation data models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VideoProvider(str, Enum):
    """Supported video generation providers."""

    HYPERFRAMES = "hyperframes"
    REMOTION = "remotion"
    VIDEOCLAW = "videoclaw"
    NONE = "none"


class VideoFormat(str, Enum):
    """Output video formats."""

    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"
    MOV = "mov"


class VideoAspectRatio(str, Enum):
    """Video aspect ratios."""

    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    CINEMATIC = "21:9"


class VideoStatus(str, Enum):
    """Video generation status."""

    PENDING = "pending"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoTemplate(BaseModel):
    """Video template model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str = ""
    html_template: str = ""
    css: str = ""
    js: str = ""
    variables: dict[str, Any] = Field(default_factory=dict)
    aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE
    duration_seconds: float = Field(default=10.0, gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoGenerationRequest(BaseModel):
    """Request model for video generation."""

    template_id: uuid.UUID | None = None
    prompt: str = Field(..., min_length=1, max_length=5000)
    provider: VideoProvider = VideoProvider.HYPERFRAMES
    format: VideoFormat = VideoFormat.MP4
    aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE
    duration_seconds: float = Field(default=10.0, gt=0, le=300)
    variables: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str | None = None


class VideoGenerationResult(BaseModel):
    """Video generation result model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: VideoStatus = VideoStatus.PENDING
    provider: VideoProvider
    video_url: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    format: VideoFormat = VideoFormat.MP4
    error_message: str | None = None
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class VideoQualityMetrics(BaseModel):
    """Video quality assessment metrics."""

    video_id: uuid.UUID
    visual_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    audio_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    pacing_score: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_prediction: float = Field(default=0.0, ge=0.0, le=1.0)
    brand_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class BatchVideoRequest(BaseModel):
    """Batch video generation request."""

    requests: list[VideoGenerationRequest] = Field(..., min_length=1, max_length=100)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class BatchVideoResult(BaseModel):
    """Batch video generation result."""

    batch_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    results: list[VideoGenerationResult] = Field(default_factory=list)
    total_requested: int = 0
    total_completed: int = 0
    total_failed: int = 0
