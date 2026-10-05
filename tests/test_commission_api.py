"""Integration tests for Commission API routes."""
from datetime import date
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


@pytest.fixture
def broker(client):
    resp = client.post(
        "/api/v1/brokers",
        json={"name": "Test Broker", "country": "SA", "currency": "SAR", "commission_rate": 0.05},
    )
    return resp.json()


def test_calculate_commission(client, broker):
    """POST /commissions/calculate returns calculated commission."""
    response = client.post(
        "/api/v1/commissions/calculate",
        json={
            "broker_id": broker["id"],
            "deal_amount": 100000.00,
            "currency": "SAR",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["broker_id"] == broker["id"]
    assert float(data["deal_amount"]) == 100000.00
    assert float(data["commission_rate"]) == 0.05
    assert float(data["commission_amount"]) == 5000.00
    assert data["currency"] == "SAR"


def test_calculate_commission_aed(client, broker):
    """Commission calculation works with AED currency."""
    response = client.post(
        "/api/v1/commissions/calculate",
        json={
            "broker_id": broker["id"],
            "deal_amount": 200000.00,
            "currency": "AED",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["commission_amount"]) == 10000.00
    assert data["currency"] == "AED"


def test_create_commission(client, broker):
    """POST /commissions creates a commission record."""
    response = client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker["id"],
            "deal_id": "DEAL-001",
            "deal_description": "Real estate deal in Riyadh",
            "deal_amount": 100000.00,
            "commission_rate": 0.05,
            "commission_amount": 5000.00,
            "currency": "SAR",
            "deal_date": "2024-01-15",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["broker_id"] == broker["id"]
    assert data["deal_id"] == "DEAL-001"
    assert float(data["commission_amount"]) == 5000.00
    assert data["status"] == "pending"


def test_list_commissions(client, broker):
    """GET /commissions returns list of commissions."""
    # Create commissions
    client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker["id"],
            "deal_id": "DEAL-001",
            "deal_amount": 10000.00,
            "commission_rate": 0.05,
            "commission_amount": 500.00,
            "currency": "SAR",
            "deal_date": "2024-01-15",
        },
    )
    client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker["id"],
            "deal_id": "DEAL-002",
            "deal_amount": 20000.00,
            "commission_rate": 0.05,
            "commission_amount": 1000.00,
            "currency": "SAR",
            "deal_date": "2024-02-01",
        },
    )

    response = client.get("/api/v1/commissions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filter_commissions_by_broker(client, broker):
    """GET /commissions?broker_id={id} filters by broker."""
    # Create commission for this broker
    client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker["id"],
            "deal_id": "DEAL-001",
            "deal_amount": 10000.00,
            "commission_rate": 0.05,
            "commission_amount": 500.00,
            "currency": "SAR",
            "deal_date": "2024-01-15",
        },
    )
    # Create another broker and commission
    broker2 = client.post(
        "/api/v1/brokers",
        json={"name": "Broker Two", "country": "AE", "currency": "AED", "commission_rate": 0.03},
    ).json()
    client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker2["id"],
            "deal_id": "DEAL-002",
            "deal_amount": 10000.00,
            "commission_rate": 0.03,
            "commission_amount": 300.00,
            "currency": "AED",
            "deal_date": "2024-01-20",
        },
    )

    response = client.get(f"/api/v1/commissions?broker_id={broker['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["broker_id"] == broker["id"]


def test_update_commission_status(client, broker):
    """PATCH /commissions/{id}/status updates commission status."""
    create_resp = client.post(
        "/api/v1/commissions",
        json={
            "broker_id": broker["id"],
            "deal_id": "DEAL-001",
            "deal_amount": 10000.00,
            "commission_rate": 0.05,
            "commission_amount": 500.00,
            "currency": "SAR",
            "deal_date": "2024-01-15",
        },
    )
    commission_id = create_resp.json()["id"]

    response = client.patch(
        f"/api/v1/commissions/{commission_id}/status",
        json={"status": "approved"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
