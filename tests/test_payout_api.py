"""Integration tests for Payout API routes."""
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
        json={"name": "Test Broker", "country": "AE", "currency": "AED", "commission_rate": 0.05},
    )
    return resp.json()


def test_create_payout(client, broker):
    """POST /payouts creates a new payout."""
    response = client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 5000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
            "reference_number": "PAY-2024-001",
            "bank_name": "Emirates NBD",
            "bank_account_last4": "1234",
            "iban": "AE070331234567890123456",
            "scheduled_date": "2024-03-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["broker_id"] == broker["id"]
    assert float(data["amount"]) == 5000.00
    assert data["currency"] == "AED"
    assert data["payout_method"] == "bank_transfer"
    assert data["status"] == "scheduled"
    assert data["reference_number"] == "PAY-2024-001"


def test_list_payouts(client, broker):
    """GET /payouts returns list of payouts."""
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 1000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
        },
    )
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 2000.00,
            "currency": "AED",
            "payout_method": "wire",
        },
    )

    response = client.get("/api/v1/payouts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filter_payouts_by_broker(client, broker):
    """GET /payouts?broker_id={id} filters by broker."""
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 1000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
        },
    )
    # Create another broker and payout
    broker2 = client.post(
        "/api/v1/brokers",
        json={"name": "Broker Two", "country": "SA", "currency": "SAR", "commission_rate": 0.03},
    ).json()
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker2["id"],
            "amount": 500.00,
            "currency": "SAR",
            "payout_method": "bank_transfer",
        },
    )

    response = client.get(f"/api/v1/payouts?broker_id={broker['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["broker_id"] == broker["id"]


def test_update_payout_status(client, broker):
    """PATCH /payouts/{id}/status updates payout status."""
    create_resp = client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 5000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
        },
    )
    payout_id = create_resp.json()["id"]

    response = client.patch(
        f"/api/v1/payouts/{payout_id}/status",
        json={"status": "processing"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"


def test_complete_payout(client, broker):
    """PATCH /payouts/{id}/status can mark payout as completed."""
    create_resp = client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 5000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
        },
    )
    payout_id = create_resp.json()["id"]

    response = client.patch(
        f"/api/v1/payouts/{payout_id}/status",
        json={"status": "completed", "completed_date": "2024-03-15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_date"] == "2024-03-15"


def test_get_payout_summary(client, broker):
    """GET /payouts/summary returns aggregated payout data."""
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 1000.00,
            "currency": "AED",
            "payout_method": "bank_transfer",
            "status": "completed",
        },
    )
    client.post(
        "/api/v1/payouts",
        json={
            "broker_id": broker["id"],
            "amount": 2000.00,
            "currency": "AED",
            "payout_method": "wire",
            "status": "scheduled",
        },
    )

    response = client.get(f"/api/v1/payouts/summary?broker_id={broker['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["broker_id"] == broker["id"]
    assert float(data["total_amount"]) == 3000.00
    assert data["currency"] == "AED"
    assert data["count"] == 2
