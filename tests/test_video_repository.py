"""Integration tests for Video repository async CRUD operations."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app import models  # noqa: F401
from app.models.base import Base
from app.models.video import (
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoQualityMetrics,
    VideoTemplate,
    GenerationStatus,
)
from app.repositories.video import (
    VideoRequestRepository,
    VideoResultRepository,
    VideoQualityMetricsRepository,
    VideoTemplateRepository,
)


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
    await engine.dispose()


class TestVideoRequestRepository:
    """Tests for VideoRequestRepository."""

    @pytest.mark.asyncio
    async def test_create_request(self, async_session):
        """Can create a video generation request."""
        repo = VideoRequestRepository(async_session)
        req = await repo.create({
            "user_id": "user-123",
            "prompt": "A cat playing piano",
            "status": GenerationStatus.PENDING,
        })
        assert req.id is not None
        assert req.user_id == "user-123"
        assert req.prompt == "A cat playing piano"
        assert req.status == GenerationStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_request_by_id(self, async_session):
        """Can retrieve a request by ID."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({
            "user_id": "user-456",
            "prompt": "Test prompt",
        })
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_request_returns_none(self, async_session):
        """Getting a non-existent request returns None."""
        repo = VideoRequestRepository(async_session)
        result = await repo.get(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_requests(self, async_session):
        """Can list all requests."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-1", "prompt": "Prompt 1"})
        await repo.create({"user_id": "user-2", "prompt": "Prompt 2"})
        await repo.create({"user_id": "user-3", "prompt": "Prompt 3"})
        results = await repo.list()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_requests_by_user(self, async_session):
        """Can filter requests by user_id."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-A", "prompt": "Prompt 1"})
        await repo.create({"user_id": "user-B", "prompt": "Prompt 2"})
        await repo.create({"user_id": "user-A", "prompt": "Prompt 3"})
        results = await repo.list(user_id="user-A")
        assert len(results) == 2
        assert all(r.user_id == "user-A" for r in results)

    @pytest.mark.asyncio
    async def test_list_requests_by_status(self, async_session):
        """Can filter requests by status."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-1", "prompt": "P1", "status": GenerationStatus.PENDING})
        await repo.create({"user_id": "user-2", "prompt": "P2", "status": GenerationStatus.COMPLETED})
        await repo.create({"user_id": "user-3", "prompt": "P3", "status": GenerationStatus.PENDING})
        results = await repo.list(status=GenerationStatus.PENDING)
        assert len(results) == 2
        assert all(r.status == GenerationStatus.PENDING for r in results)

    @pytest.mark.asyncio
    async def test_update_request(self, async_session):
        """Can update a request."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({
            "user_id": "user-123",
            "prompt": "Original prompt",
        })
        updated = await repo.update(created.id, {"prompt": "Updated prompt", "status": GenerationStatus.PROCESSING})
        assert updated is not None
        assert updated.prompt == "Updated prompt"
        assert updated.status == GenerationStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_nonexistent_request_returns_none(self, async_session):
        """Updating a non-existent request returns None."""
        repo = VideoRequestRepository(async_session)
        result = await repo.update(99999, {"prompt": "New"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_request(self, async_session):
        """Can delete a request."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({"user_id": "user-123", "prompt": "To delete"})
        deleted = await repo.delete(created.id)
        assert deleted is True
        fetched = await repo.get(created.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_request_returns_false(self, async_session):
        """Deleting a non-existent request returns False."""
        repo = VideoRequestRepository(async_session)
        result = await repo.delete(99999)
        assert result is False


class TestVideoResultRepository:
    """Tests for VideoResultRepository."""

    @pytest.mark.asyncio
    async def test_create_result(self, async_session):
        """Can create a video generation result."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})

        repo = VideoResultRepository(async_session)
        result = await repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/video.mp4",
            "duration_seconds": 15.5,
            "file_size_bytes": 1024000,
            "format": "mp4",
            "resolution": "1080p",
        })
        assert result.id is not None
        assert result.request_id == req.id
        assert result.video_url == "https://cdn.example.com/video.mp4"
        assert result.duration_seconds == 15.5

    @pytest.mark.asyncio
    async def test_get_result_by_id(self, async_session):
        """Can retrieve a result by ID."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})

        repo = VideoResultRepository(async_session)
        created = await repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "720p",
        })
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_list_results_by_request(self, async_session):
        """Can list results filtered by request_id."""
        req_repo = VideoRequestRepository(async_session)
        req1 = await req_repo.create({"user_id": "user-1", "prompt": "Test 1"})
        req2 = await req_repo.create({"user_id": "user-2", "prompt": "Test 2"})

        repo = VideoResultRepository(async_session)
        await repo.create({
            "request_id": req1.id,
            "video_url": "https://cdn.example.com/v1.mp4",
            "duration_seconds": 5.0,
            "file_size_bytes": 100000,
            "format": "mp4",
            "resolution": "1080p",
        })
        await repo.create({
            "request_id": req2.id,
            "video_url": "https://cdn.example.com/v2.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 200000,
            "format": "mp4",
            "resolution": "1080p",
        })
        results = await repo.list(request_id=req1.id)
        assert len(results) == 1
        assert results[0].request_id == req1.id

    @pytest.mark.asyncio
    async def test_update_result(self, async_session):
        """Can update a result."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})

        repo = VideoResultRepository(async_session)
        created = await repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "720p",
        })
        updated = await repo.update(created.id, {"resolution": "4K"})
        assert updated is not None
        assert updated.resolution == "4K"

    @pytest.mark.asyncio
    async def test_delete_result(self, async_session):
        """Can delete a result."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})

        repo = VideoResultRepository(async_session)
        created = await repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "1080p",
        })
        deleted = await repo.delete(created.id)
        assert deleted is True
        fetched = await repo.get(created.id)
        assert fetched is None


class TestVideoQualityMetricsRepository:
    """Tests for VideoQualityMetricsRepository."""

    @pytest.mark.asyncio
    async def test_create_metrics(self, async_session):
        """Can create quality metrics."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})
        result_repo = VideoResultRepository(async_session)
        result = await result_repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "1080p",
        })

        repo = VideoQualityMetricsRepository(async_session)
        metrics = await repo.create({
            "result_id": result.id,
            "overall_score": 85.5,
            "visual_quality": 90.0,
            "audio_quality": 80.0,
            "coherence_score": 86.5,
        })
        assert metrics.id is not None
        assert metrics.result_id == result.id
        assert metrics.overall_score == 85.5

    @pytest.mark.asyncio
    async def test_get_metrics_by_result(self, async_session):
        """Can get metrics by result_id."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})
        result_repo = VideoResultRepository(async_session)
        result = await result_repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "1080p",
        })

        repo = VideoQualityMetricsRepository(async_session)
        await repo.create({
            "result_id": result.id,
            "overall_score": 75.0,
            "visual_quality": 80.0,
            "audio_quality": 70.0,
            "coherence_score": 75.0,
        })
        metrics = await repo.get_by_result_id(result.id)
        assert metrics is not None
        assert metrics.overall_score == 75.0

    @pytest.mark.asyncio
    async def test_get_metrics_nonexistent_returns_none(self, async_session):
        """Getting metrics for non-existent result returns None."""
        repo = VideoQualityMetricsRepository(async_session)
        result = await repo.get_by_result_id(99999)
        assert result is None


class TestVideoTemplateRepository:
    """Tests for VideoTemplateRepository."""

    @pytest.mark.asyncio
    async def test_create_template(self, async_session):
        """Can create a video template."""
        repo = VideoTemplateRepository(async_session)
        template = await repo.create({
            "name": "Product Showcase",
            "description": "A template for product videos",
            "category": "marketing",
            "default_parameters": {"resolution": "1080p", "duration": 30},
        })
        assert template.id is not None
        assert template.name == "Product Showcase"
        assert template.category == "marketing"

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, async_session):
        """Can retrieve a template by ID."""
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "Test", "category": "test"})
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_list_templates(self, async_session):
        """Can list all templates."""
        repo = VideoTemplateRepository(async_session)
        await repo.create({"name": "T1", "category": "cat1"})
        await repo.create({"name": "T2", "category": "cat2"})
        results = await repo.list()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_templates_by_category(self, async_session):
        """Can filter templates by category."""
        repo = VideoTemplateRepository(async_session)
        await repo.create({"name": "T1", "category": "marketing"})
        await repo.create({"name": "T2", "category": "education"})
        await repo.create({"name": "T3", "category": "marketing"})
        results = await repo.list(category="marketing")
        assert len(results) == 2
        assert all(t.category == "marketing" for t in results)

    @pytest.mark.asyncio
    async def test_list_active_templates(self, async_session):
        """Can filter to only active templates."""
        repo = VideoTemplateRepository(async_session)
        await repo.create({"name": "Active", "category": "test", "is_active": True})
        await repo.create({"name": "Inactive", "category": "test", "is_active": False})
        results = await repo.list(active_only=True)
        assert len(results) == 1
        assert results[0].name == "Active"

    @pytest.mark.asyncio
    async def test_update_template(self, async_session):
        """Can update a template."""
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "Old Name", "category": "test"})
        updated = await repo.update(created.id, {"name": "New Name"})
        assert updated is not None
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_delete_template(self, async_session):
        """Can delete a template."""
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "To Delete", "category": "test"})
        deleted = await repo.delete(created.id)
        assert deleted is True
        fetched = await repo.get(created.id)
        assert fetched is None
