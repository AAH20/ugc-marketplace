"""Video generation models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    Text,
    JSON,
    Enum as SQLEnum,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class GenerationStatus(str, enum.Enum):
    """Status of a video generation request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoGenerationRequest(Base, TimestampMixin):
    """A request to generate a video."""

    __tablename__ = "video_generation_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("video_templates.id"), nullable=True
    )
    status: Mapped[GenerationStatus] = mapped_column(
        SQLEnum(GenerationStatus), nullable=False, default=GenerationStatus.PENDING
    )
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    template: Mapped[Optional["VideoTemplate"]] = relationship(
        "VideoTemplate", back_populates="requests"
    )
    results: Mapped[list["VideoGenerationResult"]] = relationship(
        "VideoGenerationResult", back_populates="request", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<VideoGenerationRequest(id={self.id}, user_id='{self.user_id}', status='{self.status}')>"


class VideoGenerationResult(Base, TimestampMixin):
    """The result of a video generation."""

    __tablename__ = "video_generation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("video_generation_requests.id"), nullable=False, index=True
    )
    video_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False)

    request: Mapped["VideoGenerationRequest"] = relationship(
        "VideoGenerationRequest", back_populates="results"
    )
    quality_metrics: Mapped[list["VideoQualityMetrics"]] = relationship(
        "VideoQualityMetrics", back_populates="result", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<VideoGenerationResult(id={self.id}, request_id={self.request_id}, format='{self.format}')>"


class VideoQualityMetrics(Base, TimestampMixin):
    """Quality metrics for a generated video."""

    __tablename__ = "video_quality_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("video_generation_results.id"), nullable=False, index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    visual_quality: Mapped[float] = mapped_column(Float, nullable=False)
    audio_quality: Mapped[float] = mapped_column(Float, nullable=False)
    coherence_score: Mapped[float] = mapped_column(Float, nullable=False)

    result: Mapped["VideoGenerationResult"] = relationship(
        "VideoGenerationResult", back_populates="quality_metrics"
    )

    def __repr__(self):
        return f"<VideoQualityMetrics(id={self.id}, result_id={self.result_id}, overall_score={self.overall_score})>"


class VideoTemplate(Base, TimestampMixin):
    """A reusable video generation template."""

    __tablename__ = "video_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    default_parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    requests: Mapped[list["VideoGenerationRequest"]] = relationship(
        "VideoGenerationRequest", back_populates="template"
    )

    def __repr__(self):
        return f"<VideoTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
