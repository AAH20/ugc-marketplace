"""Integration tests for Broker API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models  # noqa: F401
from app.main import app, get_db
from app.models.base import Base


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_broker(client):
    """POST /brokers creates a new broker."""
    response = client.post(
        "/api/v1/brokers",
        json={
            "name": "Dubai Creators Hub",
            "name_ar": "دبي كرييتورز هب",
            "country": "AE",
            "currency": "AED",
            "commission_rate": 0.05,
            "contact_email": "broker@example.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Dubai Creators Hub"
    assert data["name_ar"] == "دبي كرييتورز هب"
    assert data["country"] == "AE"
    assert data["currency"] == "AED"
    assert float(data["commission_rate"]) == 0.05
    assert data["id"] is not None


def test_create_broker_invalid_currency(client):
    """POST /brokers rejects non-MENA currency."""
    response = client.post(
        "/api/v1/brokers",
        json={
            "name": "Test Broker",
            "country": "AE",
            "currency": "USD",
            "commission_rate": 0.05,
        },
    )
    assert response.status_code == 422


def test_create_broker_invalid_country(client):
    """POST /brokers rejects non-MENA country."""
    response = client.post(
        "/api/v1/brokers",
        json={
            "name": "Test Broker",
            "country": "US",
            "currency": "USD",
            "commission_rate": 0.05,
        },
    )
    assert response.status_code == 422


def test_list_brokers(client):
    """GET /brokers returns list of brokers."""
    # Create two brokers
    client.post(
        "/api/v1/brokers",
        json={"name": "Broker One", "country": "AE", "currency": "AED", "commission_rate": 0.05},
    )
    client.post(
        "/api/v1/brokers",
        json={"name": "Broker Two", "country": "SA", "currency": "SAR", "commission_rate": 0.03},
    )

    response = client.get("/api/v1/brokers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {b["name"] for b in data}
    assert names == {"Broker One", "Broker Two"}


def test_get_broker(client):
    """GET /brokers/{id} returns a specific broker."""
    create_resp = client.post(
        "/api/v1/brokers",
        json={"name": "Test Broker", "country": "AE", "currency": "AED", "commission_rate": 0.05},
    )
    broker_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/brokers/{broker_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == broker_id
    assert data["name"] == "Test Broker"


def test_get_broker_not_found(client):
    """GET /brokers/{id} returns 404 for non-existent broker."""
    response = client.get("/api/v1/brokers/9999")
    assert response.status_code == 404


def test_update_broker(client):
    """PUT /brokers/{id} updates a broker."""
    create_resp = client.post(
        "/api/v1/brokers",
        json={"name": "Test Broker", "country": "AE", "currency": "AED", "commission_rate": 0.05},
    )
    broker_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/brokers/{broker_id}",
        json={"commission_rate": 0.08, "is_active": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["commission_rate"]) == 0.08
    assert data["is_active"] is False


def test_delete_broker(client):
    """DELETE /brokers/{id} deletes a broker."""
    create_resp = client.post(
        "/api/v1/brokers",
        json={"name": "Test Broker", "country": "AE", "currency": "AED", "commission_rate": 0.05},
    )
    broker_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/brokers/{broker_id}")
    assert response.status_code == 204

    # Verify deletion
    get_resp = client.get(f"/api/v1/brokers/{broker_id}")
    assert get_resp.status_code == 404
