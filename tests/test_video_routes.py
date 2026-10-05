"""Integration tests for Video API routes."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.models.base import Base
from app.models.video import GenerationStatus
from app.repositories.video import VideoRequestRepository


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_session):
    from app.main import app
    from app.gtm.db import get_gtm_session

    async def override_get_session():
        yield async_session

    app.dependency_overrides[get_gtm_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestVideoRequestRoutes:
    """Tests for video request API endpoints."""

    @pytest.mark.asyncio
    async def test_create_video_request(self, client):
        """POST /api/v1/video/requests creates a new request."""
        response = await client.post("/api/v1/video/requests", json={
            "user_id": "user-123",
            "prompt": "A cat playing piano",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["prompt"] == "A cat playing piano"
        assert data["status"] == "pending"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_request_with_template(self, client, async_session):
        """POST /api/v1/video/requests with template_id."""
        from app.repositories.video import VideoTemplateRepository
        template_repo = VideoTemplateRepository(async_session)
        template = await template_repo.create({
            "name": "Test Template",
            "category": "test",
        })

        response = await client.post("/api/v1/video/requests", json={
            "user_id": "user-456",
            "prompt": "Test prompt",
            "template_id": template.id,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["template_id"] == template.id

    @pytest.mark.asyncio
    async def test_create_request_with_parameters(self, client):
        """POST /api/v1/video/requests with custom parameters."""
        response = await client.post("/api/v1/video/requests", json={
            "user_id": "user-789",
            "prompt": "Test",
            "parameters": {"resolution": "4K", "fps": 60},
        })
        assert response.status_code == 201
        data = response.json()
        assert data["parameters"]["resolution"] == "4K"
        assert data["parameters"]["fps"] == 60

    @pytest.mark.asyncio
    async def test_get_video_request(self, client, async_session):
        """GET /api/v1/video/requests/{id} retrieves a request."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({
            "user_id": "user-123",
            "prompt": "Test prompt",
        })

        response = await client.get(f"/api/v1/video/requests/{created.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created.id
        assert data["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_request_returns_404(self, client):
        """GET /api/v1/video/requests/{id} returns 404 for non-existent."""
        response = await client.get("/api/v1/video/requests/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_video_requests(self, client, async_session):
        """GET /api/v1/video/requests lists all requests."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-1", "prompt": "P1"})
        await repo.create({"user_id": "user-2", "prompt": "P2"})

        response = await client.get("/api/v1/video/requests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_requests_filter_by_user(self, client, async_session):
        """GET /api/v1/video/requests?user_id= filters by user."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-A", "prompt": "P1"})
        await repo.create({"user_id": "user-B", "prompt": "P2"})
        await repo.create({"user_id": "user-A", "prompt": "P3"})

        response = await client.get("/api/v1/video/requests?user_id=user-A")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(r["user_id"] == "user-A" for r in data)

    @pytest.mark.asyncio
    async def test_list_requests_filter_by_status(self, client, async_session):
        """GET /api/v1/video/requests?status= filters by status."""
        repo = VideoRequestRepository(async_session)
        await repo.create({"user_id": "user-1", "prompt": "P1", "status": GenerationStatus.PENDING})
        await repo.create({"user_id": "user-2", "prompt": "P2", "status": GenerationStatus.COMPLETED})

        response = await client.get("/api/v1/video/requests?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_video_request(self, client, async_session):
        """PATCH /api/v1/video/requests/{id} updates a request."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({
            "user_id": "user-123",
            "prompt": "Original",
        })

        response = await client.patch(f"/api/v1/video/requests/{created.id}", json={
            "prompt": "Updated",
            "status": "processing",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == "Updated"
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_nonexistent_request_returns_404(self, client):
        """PATCH /api/v1/video/requests/{id} returns 404 for non-existent."""
        response = await client.patch("/api/v1/video/requests/99999", json={"prompt": "New"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_video_request(self, client, async_session):
        """DELETE /api/v1/video/requests/{id} deletes a request."""
        repo = VideoRequestRepository(async_session)
        created = await repo.create({"user_id": "user-123", "prompt": "To delete"})

        response = await client.delete(f"/api/v1/video/requests/{created.id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/v1/video/requests/{created.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_request_returns_404(self, client):
        """DELETE /api/v1/video/requests/{id} returns 404 for non-existent."""
        response = await client.delete("/api/v1/video/requests/99999")
        assert response.status_code == 404


class TestVideoTemplateRoutes:
    """Tests for video template API endpoints."""

    @pytest.mark.asyncio
    async def test_create_template(self, client):
        """POST /api/v1/video/templates creates a template."""
        response = await client.post("/api/v1/video/templates", json={
            "name": "Product Showcase",
            "description": "A template for product videos",
            "category": "marketing",
            "default_parameters": {"resolution": "1080p"},
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Product Showcase"
        assert data["category"] == "marketing"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_template(self, client, async_session):
        """GET /api/v1/video/templates/{id} retrieves a template."""
        from app.repositories.video import VideoTemplateRepository
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "Test", "category": "test"})

        response = await client.get(f"/api/v1/video/templates/{created.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created.id
        assert data["name"] == "Test"

    @pytest.mark.asyncio
    async def test_list_templates(self, client, async_session):
        """GET /api/v1/video/templates lists all templates."""
        from app.repositories.video import VideoTemplateRepository
        repo = VideoTemplateRepository(async_session)
        await repo.create({"name": "T1", "category": "cat1"})
        await repo.create({"name": "T2", "category": "cat2"})

        response = await client.get("/api/v1/video/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_category(self, client, async_session):
        """GET /api/v1/video/templates?category= filters by category."""
        from app.repositories.video import VideoTemplateRepository
        repo = VideoTemplateRepository(async_session)
        await repo.create({"name": "T1", "category": "marketing"})
        await repo.create({"name": "T2", "category": "education"})

        response = await client.get("/api/v1/video/templates?category=marketing")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "marketing"

    @pytest.mark.asyncio
    async def test_update_template(self, client, async_session):
        """PATCH /api/v1/video/templates/{id} updates a template."""
        from app.repositories.video import VideoTemplateRepository
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "Old", "category": "test"})

        response = await client.patch(f"/api/v1/video/templates/{created.id}", json={
            "name": "New Name",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_template(self, client, async_session):
        """DELETE /api/v1/video/templates/{id} deletes a template."""
        from app.repositories.video import VideoTemplateRepository
        repo = VideoTemplateRepository(async_session)
        created = await repo.create({"name": "To Delete", "category": "test"})

        response = await client.delete(f"/api/v1/video/templates/{created.id}")
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/video/templates/{created.id}")
        assert get_response.status_code == 404


class TestVideoResultRoutes:
    """Tests for video result API endpoints."""

    @pytest.mark.asyncio
    async def test_create_result(self, client, async_session):
        """POST /api/v1/video/results creates a result."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})

        response = await client.post("/api/v1/video/results", json={
            "request_id": req.id,
            "video_url": "https://cdn.example.com/video.mp4",
            "duration_seconds": 15.5,
            "file_size_bytes": 1024000,
            "format": "mp4",
            "resolution": "1080p",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["request_id"] == req.id
        assert data["video_url"] == "https://cdn.example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_get_result(self, client, async_session):
        """GET /api/v1/video/results/{id} retrieves a result."""
        req_repo = VideoRequestRepository(async_session)
        req = await req_repo.create({"user_id": "user-1", "prompt": "Test"})
        from app.repositories.video import VideoResultRepository
        result_repo = VideoResultRepository(async_session)
        created = await result_repo.create({
            "request_id": req.id,
            "video_url": "https://cdn.example.com/v.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 500000,
            "format": "mp4",
            "resolution": "1080p",
        })

        response = await client.get(f"/api/v1/video/results/{created.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created.id

    @pytest.mark.asyncio
    async def test_list_results_by_request(self, client, async_session):
        """GET /api/v1/video/results?request_id= filters by request."""
        req_repo = VideoRequestRepository(async_session)
        req1 = await req_repo.create({"user_id": "user-1", "prompt": "Test 1"})
        req2 = await req_repo.create({"user_id": "user-2", "prompt": "Test 2"})
        from app.repositories.video import VideoResultRepository
        result_repo = VideoResultRepository(async_session)
        await result_repo.create({
            "request_id": req1.id,
            "video_url": "https://cdn.example.com/v1.mp4",
            "duration_seconds": 5.0,
            "file_size_bytes": 100000,
            "format": "mp4",
            "resolution": "1080p",
        })
        await result_repo.create({
            "request_id": req2.id,
            "video_url": "https://cdn.example.com/v2.mp4",
            "duration_seconds": 10.0,
            "file_size_bytes": 200000,
            "format": "mp4",
            "resolution": "1080p",
        })

        response = await client.get(f"/api/v1/video/results?request_id={req1.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["request_id"] == req1.id
