"""Integration tests for Video models."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models  # noqa: F401
from app.models.base import Base
from app.models.video import (
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoQualityMetrics,
    VideoTemplate,
    GenerationStatus,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestVideoGenerationRequest:
    """Tests for VideoGenerationRequest model."""

    def test_create_request_with_required_fields(self, db_session):
        """Can create a request with minimal required fields."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="A cat playing piano",
            status=GenerationStatus.PENDING,
        )
        db_session.add(req)
        db_session.commit()

        assert req.id is not None
        assert req.user_id == "user-123"
        assert req.prompt == "A cat playing piano"
        assert req.status == GenerationStatus.PENDING
        assert req.created_at is not None
        assert req.updated_at is not None

    def test_create_request_with_template(self, db_session):
        """Can create a request linked to a template."""
        template = VideoTemplate(
            name="Piano Cat",
            category="animals",
            default_parameters={"resolution": "1080p", "duration": 10},
        )
        db_session.add(template)
        db_session.commit()

        req = VideoGenerationRequest(
            user_id="user-456",
            prompt="A cat playing piano",
            template_id=template.id,
            status=GenerationStatus.PENDING,
        )
        db_session.add(req)
        db_session.commit()

        assert req.template_id == template.id
        assert req.template.name == "Piano Cat"

    def test_request_status_defaults_to_pending(self, db_session):
        """Status defaults to PENDING when not specified."""
        req = VideoGenerationRequest(
            user_id="user-789",
            prompt="Test prompt",
        )
        db_session.add(req)
        db_session.commit()

        assert req.status == GenerationStatus.PENDING

    def test_request_parameters_default_to_empty_dict(self, db_session):
        """Parameters default to empty dict."""
        req = VideoGenerationRequest(
            user_id="user-000",
            prompt="Test",
        )
        db_session.add(req)
        db_session.commit()

        assert req.parameters == {}

    def test_request_can_have_parameters(self, db_session):
        """Can store generation parameters as JSON."""
        req = VideoGenerationRequest(
            user_id="user-111",
            prompt="Test",
            parameters={"resolution": "4K", "fps": 60, "style": "cinematic"},
        )
        db_session.add(req)
        db_session.commit()

        assert req.parameters["resolution"] == "4K"
        assert req.parameters["fps"] == 60
        assert req.parameters["style"] == "cinematic"


class TestVideoGenerationResult:
    """Tests for VideoGenerationResult model."""

    def test_create_result(self, db_session):
        """Can create a result linked to a request."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="Test",
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(req)
        db_session.commit()

        result = VideoGenerationResult(
            request_id=req.id,
            video_url="https://cdn.example.com/video.mp4",
            duration_seconds=15.5,
            file_size_bytes=1024000,
            format="mp4",
            resolution="1080p",
        )
        db_session.add(result)
        db_session.commit()

        assert result.id is not None
        assert result.request_id == req.id
        assert result.video_url == "https://cdn.example.com/video.mp4"
        assert result.duration_seconds == 15.5
        assert result.file_size_bytes == 1024000
        assert result.format == "mp4"
        assert result.resolution == "1080p"

    def test_result_can_have_thumbnail(self, db_session):
        """Result can have a thumbnail URL."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="Test",
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(req)
        db_session.commit()

        result = VideoGenerationResult(
            request_id=req.id,
            video_url="https://cdn.example.com/video.mp4",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            duration_seconds=10.0,
            file_size_bytes=500000,
            format="mp4",
            resolution="720p",
        )
        db_session.add(result)
        db_session.commit()

        assert result.thumbnail_url == "https://cdn.example.com/thumb.jpg"

    def test_result_belongs_to_request(self, db_session):
        """Result is accessible from its parent request."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="Test",
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(req)
        db_session.commit()

        result = VideoGenerationResult(
            request_id=req.id,
            video_url="https://cdn.example.com/video.mp4",
            duration_seconds=5.0,
            file_size_bytes=100000,
            format="mp4",
            resolution="1080p",
        )
        db_session.add(result)
        db_session.commit()

        assert len(req.results) == 1
        assert req.results[0].video_url == "https://cdn.example.com/video.mp4"


class TestVideoQualityMetrics:
    """Tests for VideoQualityMetrics model."""

    def test_create_quality_metrics(self, db_session):
        """Can create quality metrics for a result."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="Test",
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(req)
        db_session.commit()

        result = VideoGenerationResult(
            request_id=req.id,
            video_url="https://cdn.example.com/video.mp4",
            duration_seconds=10.0,
            file_size_bytes=500000,
            format="mp4",
            resolution="1080p",
        )
        db_session.add(result)
        db_session.commit()

        metrics = VideoQualityMetrics(
            result_id=result.id,
            overall_score=85.5,
            visual_quality=90.0,
            audio_quality=80.0,
            coherence_score=86.5,
        )
        db_session.add(metrics)
        db_session.commit()

        assert metrics.id is not None
        assert metrics.result_id == result.id
        assert metrics.overall_score == 85.5
        assert metrics.visual_quality == 90.0
        assert metrics.audio_quality == 80.0
        assert metrics.coherence_score == 86.5

    def test_quality_metrics_belong_to_result(self, db_session):
        """Quality metrics accessible from parent result."""
        req = VideoGenerationRequest(
            user_id="user-123",
            prompt="Test",
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(req)
        db_session.commit()

        result = VideoGenerationResult(
            request_id=req.id,
            video_url="https://cdn.example.com/video.mp4",
            duration_seconds=10.0,
            file_size_bytes=500000,
            format="mp4",
            resolution="1080p",
        )
        db_session.add(result)
        db_session.commit()

        metrics = VideoQualityMetrics(
            result_id=result.id,
            overall_score=75.0,
            visual_quality=80.0,
            audio_quality=70.0,
            coherence_score=75.0,
        )
        db_session.add(metrics)
        db_session.commit()

        assert len(result.quality_metrics) == 1
        assert result.quality_metrics[0].overall_score == 75.0


class TestVideoTemplate:
    """Tests for VideoTemplate model."""

    def test_create_template(self, db_session):
        """Can create a video template."""
        template = VideoTemplate(
            name="Product Showcase",
            description="A template for product videos",
            category="marketing",
            default_parameters={"resolution": "1080p", "duration": 30, "style": "professional"},
            is_active=True,
        )
        db_session.add(template)
        db_session.commit()

        assert template.id is not None
        assert template.name == "Product Showcase"
        assert template.description == "A template for product videos"
        assert template.category == "marketing"
        assert template.default_parameters["resolution"] == "1080p"
        assert template.is_active is True

    def test_template_is_active_by_default(self, db_session):
        """Template is active by default."""
        template = VideoTemplate(
            name="Test Template",
            category="test",
        )
        db_session.add(template)
        db_session.commit()

        assert template.is_active is True

    def test_template_parameters_default_to_empty(self, db_session):
        """Template parameters default to empty dict."""
        template = VideoTemplate(
            name="Test",
            category="test",
        )
        db_session.add(template)
        db_session.commit()

        assert template.default_parameters == {}

    def test_template_can_be_deactivated(self, db_session):
        """Template can be deactivated."""
        template = VideoTemplate(
            name="Test",
            category="test",
            is_active=False,
        )
        db_session.add(template)
        db_session.commit()

        assert template.is_active is False
