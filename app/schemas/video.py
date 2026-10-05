"""Pydantic schemas for video generation API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.models.video import GenerationStatus


class VideoRequestCreate(BaseModel):
    """Schema for creating a video generation request."""
    user_id: str
    prompt: str
    template_id: Optional[int] = None
    parameters: dict = Field(default_factory=dict)


class VideoRequestUpdate(BaseModel):
    """Schema for updating a video generation request."""
    prompt: Optional[str] = None
    status: Optional[GenerationStatus] = None
    parameters: Optional[dict] = None
    error_message: Optional[str] = None


class VideoRequestResponse(BaseModel):
    """Schema for video generation request response."""
    id: int
    user_id: str
    prompt: str
    template_id: Optional[int] = None
    status: GenerationStatus
    parameters: dict
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoResultCreate(BaseModel):
    """Schema for creating a video generation result."""
    request_id: int
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: float
    file_size_bytes: int
    format: str
    resolution: str


class VideoResultUpdate(BaseModel):
    """Schema for updating a video generation result."""
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None
    resolution: Optional[str] = None


class VideoResultResponse(BaseModel):
    """Schema for video generation result response."""
    id: int
    request_id: int
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: float
    file_size_bytes: int
    format: str
    resolution: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoQualityMetricsCreate(BaseModel):
    """Schema for creating quality metrics."""
    result_id: int
    overall_score: float
    visual_quality: float
    audio_quality: float
    coherence_score: float


class VideoQualityMetricsResponse(BaseModel):
    """Schema for quality metrics response."""
    id: int
    result_id: int
    overall_score: float
    visual_quality: float
    audio_quality: float
    coherence_score: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoTemplateCreate(BaseModel):
    """Schema for creating a video template."""
    name: str
    description: Optional[str] = None
    category: str
    default_parameters: dict = Field(default_factory=dict)
    is_active: bool = True


class VideoTemplateUpdate(BaseModel):
    """Schema for updating a video template."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    default_parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class VideoTemplateResponse(BaseModel):
    """Schema for video template response."""
    id: int
    name: str
    description: Optional[str] = None
    category: str
    default_parameters: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
