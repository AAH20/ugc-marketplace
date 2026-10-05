"""Integration tests for GTM LaunchCampaign API (database-backed)."""
import uuid

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.gtm.api.routes import router
from app.gtm.db import get_gtm_session
from app.models.base import Base


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_session):
    app = FastAPI()
    app.include_router(router)

    async def override_get_gtm_session():
        yield async_session

    app.dependency_overrides[get_gtm_session] = override_get_gtm_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _payload(**overrides):
    data = {
        "name": "Ramadan Launch",
        "description": "MENA creator push",
        "channels": ["instagram", "tiktok"],
        "content_type": "video",
        "target_audience": "18-34 GCC",
        "budget": 5000.0,
        "status": "draft",
        "extra_metadata": {"region": "GCC", "language": "ar"},
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_campaign(client):
    resp = await client.post("/api/v1/gtm/campaigns", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ramadan Launch"
    assert body["status"] == "draft"
    assert body["channels"] == ["instagram", "tiktok"]
    assert body["extra_metadata"] == {"region": "GCC", "language": "ar"}
    assert uuid.UUID(body["id"])


@pytest.mark.asyncio
async def test_create_campaign_validation_error(client):
    resp = await client.post("/api/v1/gtm/campaigns", json={"budget": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_campaigns(client):
    await client.post("/api/v1/gtm/campaigns", json=_payload(name="A"))
    await client.post("/api/v1/gtm/campaigns", json=_payload(name="B"))
    resp = await client.get("/api/v1/gtm/campaigns")
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert names == {"A", "B"}


@pytest.mark.asyncio
async def test_get_campaign(client):
    created = (await client.post("/api/v1/gtm/campaigns", json=_payload())).json()
    resp = await client.get(f"/api/v1/gtm/campaigns/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_campaign_not_found(client):
    resp = await client.get(f"/api/v1/gtm/campaigns/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_campaign(client):
    created = (await client.post("/api/v1/gtm/campaigns", json=_payload())).json()
    resp = await client.put(
        f"/api/v1/gtm/campaigns/{created['id']}",
        json={"status": "active", "budget": 7500.0, "channels": ["instagram"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "active"
    assert float(body["budget"]) == 7500.0
    assert body["channels"] == ["instagram"]


@pytest.mark.asyncio
async def test_update_campaign_not_found(client):
    resp = await client.put(f"/api/v1/gtm/campaigns/{uuid.uuid4()}", json={"status": "active"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign(client):
    created = (await client.post("/api/v1/gtm/campaigns", json=_payload())).json()
    resp = await client.delete(f"/api/v1/gtm/campaigns/{created['id']}")
    assert resp.status_code == 204
    assert (await client.get(f"/api/v1/gtm/campaigns/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign_not_found(client):
    resp = await client.delete(f"/api/v1/gtm/campaigns/{uuid.uuid4()}")
    assert resp.status_code == 404
