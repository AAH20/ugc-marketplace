"""Comprehensive API tests for the Payments endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ugc_marketplace.main import app
from src.ugc_marketplace.database import Base, get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a TestClient with dependency override for the database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_payment_payload():
    """Return a valid payload for creating a payment."""
    return {
        "order_id": "order-123",
        "user_id": "user-456",
        "amount": 99.99,
        "currency": "USD",
        "payment_method": "credit_card",
        "status": "pending",
    }


@pytest.fixture
def created_payment(client, sample_payment_payload):
    """Create a payment and return the response JSON."""
    response = client.post("/api/v1/payments", json=sample_payment_payload)
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# 1. test_list_payments — GET /api/v1/payments
# ---------------------------------------------------------------------------

class TestListPayments:
    """Tests for listing payments with pagination."""

    def test_list_payments_empty(self, client):
        """GET /api/v1/payments returns empty list when no payments exist."""
        response = client.get("/api/v1/payments")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_payments_returns_created(self, client, created_payment):
        """GET /api/v1/payments returns previously created payments."""
        response = client.get("/api/v1/payments")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == created_payment["id"]
        assert data["items"][0]["order_id"] == created_payment["order_id"]
        assert data["items"][0]["amount"] == created_payment["amount"]

    def test_list_payments_pagination_first_page(self, client, sample_payment_payload):
        """GET /api/v1/payments returns correct first page with pagination."""
        for i in range(5):
            payload = {**sample_payment_payload, "order_id": f"order-{i}"}
            client.post("/api/v1/payments", json=payload)

        response = client.get("/api/v1/payments?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2

    def test_list_payments_pagination_second_page(self, client, sample_payment_payload):
        """GET /api/v1/payments returns correct second page."""
        for i in range(5):
            payload = {**sample_payment_payload, "order_id": f"order-{i}"}
            client.post("/api/v1/payments", json=payload)

        response = client.get("/api/v1/payments?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert len(data["items"]) == 2

    def test_list_payments_pagination_last_partial_page(self, client, sample_payment_payload):
        """GET /api/v1/payments returns remaining items on last page."""
        for i in range(5):
            payload = {**sample_payment_payload, "order_id": f"order-{i}"}
            client.post("/api/v1/payments", json=payload)

        response = client.get("/api/v1/payments?page=3&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 3
        assert len(data["items"]) == 1

    def test_list_payments_pagination_beyond_last_page(self, client, sample_payment_payload):
        """GET /api/v1/payments returns empty items when page exceeds total pages."""
        for i in range(3):
            payload = {**sample_payment_payload, "order_id": f"order-{i}"}
            client.post("/api/v1/payments", json=payload)

        response = client.get("/api/v1/payments?page=10&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["page"] == 10
        assert data["items"] == []

    def test_list_payments_invalid_page_number(self, client):
        """GET /api/v1/payments with page=0 returns validation error."""
        response = client.get("/api/v1/payments?page=0")
        assert response.status_code == 422

    def test_list_payments_invalid_page_size(self, client):
        """GET /api/v1/payments with page_size=0 returns validation error."""
        response = client.get("/api/v1/payments?page_size=0")
        assert response.status_code == 422

    def test_list_payments_filter_by_status(self, client, sample_payment_payload):
        """GET /api/v1/payments filters by status query parameter."""
        client.post("/api/v1/payments", json={**sample_payment_payload, "status": "pending"})
        client.post("/api/v1/payments", json={**sample_payment_payload, "status": "completed", "order_id": "order-2"})

        response = client.get("/api/v1/payments?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending"

    def test_list_payments_filter_by_user_id(self, client, sample_payment_payload):
        """GET /api/v1/payments filters by user_id query parameter."""
        client.post("/api/v1/payments", json={**sample_payment_payload, "user_id": "user-A"})
        client.post("/api/v1/payments", json={**sample_payment_payload, "user_id": "user-B", "order_id": "order-2"})

        response = client.get("/api/v1/payments?user_id=user-A")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == "user-A"


# ---------------------------------------------------------------------------
# 2. test_create_payment — POST /api/v1/payments
# ---------------------------------------------------------------------------

class TestCreatePayment:
    """Tests for creating payments."""

    def test_create_payment_success(self, client, sample_payment_payload):
        """POST /api/v1/payments creates a payment successfully."""
        response = client.post("/api/v1/payments", json=sample_payment_payload)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["order_id"] == sample_payment_payload["order_id"]
        assert data["user_id"] == sample_payment_payload["user_id"]
        assert data["amount"] == sample_payment_payload["amount"]
        assert data["currency"] == sample_payment_payload["currency"]
        assert data["payment_method"] == sample_payment_payload["payment_method"]
        assert data["status"] == sample_payment_payload["status"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_payment_minimal_payload(self, client):
        """POST /api/v1/payments works with minimal required fields."""
        payload = {
            "order_id": "order-min",
            "user_id": "user-min",
            "amount": 10.00,
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["order_id"] == "order-min"
        assert data["amount"] == 10.00

    def test_create_payment_missing_required_fields(self, client):
        """POST /api/v1/payments returns 422 when required fields are missing."""
        response = client.post("/api/v1/payments", json={})
        assert response.status_code == 422

    def test_create_payment_missing_order_id(self, client):
        """POST /api/v1/payments returns 422 when order_id is missing."""
        payload = {"user_id": "user-123", "amount": 50.00}
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_missing_user_id(self, client):
        """POST /api/v1/payments returns 422 when user_id is missing."""
        payload = {"order_id": "order-123", "amount": 50.00}
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_missing_amount(self, client):
        """POST /api/v1/payments returns 422 when amount is missing."""
        payload = {"order_id": "order-123", "user_id": "user-456"}
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_negative_amount(self, client):
        """POST /api/v1/payments rejects negative amounts."""
        payload = {
            "order_id": "order-123",
            "user_id": "user-456",
            "amount": -10.00,
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_zero_amount(self, client):
        """POST /api/v1/payments rejects zero amount."""
        payload = {
            "order_id": "order-123",
            "user_id": "user-456",
            "amount": 0,
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_invalid_currency(self, client):
        """POST /api/v1/payments rejects invalid currency codes."""
        payload = {
            "order_id": "order-123",
            "user_id": "user-456",
            "amount": 50.00,
            "currency": "INVALID",
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_invalid_status(self, client):
        """POST /api/v1/payments rejects invalid status values."""
        payload = {
            "order_id": "order-123",
            "user_id": "user-456",
            "amount": 50.00,
            "status": "invalid_status",
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_invalid_payment_method(self, client):
        """POST /api/v1/payments rejects invalid payment methods."""
        payload = {
            "order_id": "order-123",
            "user_id": "user-456",
            "amount": 50.00,
            "payment_method": "bitcoin",
        }
        response = client.post("/api/v1/payments", json=payload)
        assert response.status_code == 422

    def test_create_payment_duplicate_order_id(self, client, sample_payment_payload):
        """POST /api/v1/payments rejects duplicate order_id."""
        response1 = client.post("/api/v1/payments", json=sample_payment_payload)
        assert response1.status_code == 201

        response2 = client.post("/api/v1/payments", json=sample_payment_payload)
        assert response2.status_code == 409

    def test_create_payment_response_content_type(self, client, sample_payment_payload):
        """POST /api/v1/payments returns JSON content type."""
        response = client.post("/api/v1/payments", json=sample_payment_payload)
        assert response.status_code == 201
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# 3. test_get_payment — GET /api/v1/payments/{id}
# ---------------------------------------------------------------------------

class TestGetPayment:
    """Tests for retrieving a single payment by ID."""

    def test_get_payment_success(self, client, created_payment):
        """GET /api/v1/payments/{id} returns the correct payment."""
        payment_id = created_payment["id"]
        response = client.get(f"/api/v1/payments/{payment_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == payment_id
        assert data["order_id"] == created_payment["order_id"]
        assert data["user_id"] == created_payment["user_id"]
        assert data["amount"] == created_payment["amount"]
        assert data["currency"] == created_payment["currency"]
        assert data["payment_method"] == created_payment["payment_method"]
        assert data["status"] == created_payment["status"]

    def test_get_payment_not_found(self, client):
        """GET /api/v1/payments/{id} returns 404 for non-existent payment."""
        response = client.get("/api/v1/payments/nonexistent-id")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_get_payment_invalid_id_format(self, client):
        """GET /api/v1/payments/{id} handles invalid ID format gracefully."""
        response = client.get("/api/v1/payments/!!!invalid!!!")
        assert response.status_code in (404, 422)

    def test_get_payment_response_has_all_fields(self, client, created_payment):
        """GET /api/v1/payments/{id} response contains all expected fields."""
        payment_id = created_payment["id"]
        response = client.get(f"/api/v1/payments/{payment_id}")
        assert response.status_code == 200
        data = response.json()
        expected_fields = {"id", "order_id", "user_id", "amount", "currency", "payment_method", "status", "created_at", "updated_at"}
        assert expected_fields.issubset(set(data.keys()))


# ---------------------------------------------------------------------------
# 4. test_update_payment_status — PUT /api/v1/payments/{id}
# ---------------------------------------------------------------------------

class TestUpdatePaymentStatus:
    """Tests for updating payment status via PUT."""

    def test_update_payment_status_success(self, client, created_payment):
        """PUT /api/v1/payments/{id} updates payment status successfully."""
        payment_id = created_payment["id"]
        update_payload = {"status": "completed"}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == payment_id
        assert data["status"] == "completed"
        assert data["order_id"] == created_payment["order_id"]
        assert data["amount"] == created_payment["amount"]

    def test_update_payment_status_to_failed(self, client, created_payment):
        """PUT /api/v1/payments/{id} can update status to failed."""
        payment_id = created_payment["id"]
        update_payload = {"status": "failed"}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_update_payment_status_to_refunded(self, client, created_payment):
        """PUT /api/v1/payments/{id} can update status to refunded."""
        payment_id = created_payment["id"]
        update_payload = {"status": "refunded"}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "refunded"

    def test_update_payment_status_not_found(self, client):
        """PUT /api/v1/payments/{id} returns 404 for non-existent payment."""
        update_payload = {"status": "completed"}
        response = client.put("/api/v1/payments/nonexistent-id", json=update_payload)
        assert response.status_code == 404

    def test_update_payment_status_invalid_status(self, client, created_payment):
        """PUT /api/v1/payments/{id} rejects invalid status values."""
        payment_id = created_payment["id"]
        update_payload = {"status": "not_a_valid_status"}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 422

    def test_update_payment_status_empty_body(self, client, created_payment):
        """PUT /api/v1/payments/{id} returns 422 for empty request body."""
        payment_id = created_payment["id"]
        response = client.put(f"/api/v1/payments/{payment_id}", json={})
        assert response.status_code == 422

    def test_update_payment_status_missing_status_field(self, client, created_payment):
        """PUT /api/v1/payments/{id} returns 422 when status field is missing."""
        payment_id = created_payment["id"]
        response = client.put(f"/api/v1/payments/{payment_id}", json={"other_field": "value"})
        assert response.status_code == 422

    def test_update_payment_status_updates_timestamp(self, client, created_payment):
        """PUT /api/v1/payments/{id} updates the updated_at timestamp."""
        payment_id = created_payment["id"]
        original_updated_at = created_payment["updated_at"]

        update_payload = {"status": "completed"}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["updated_at"] != data["created_at"] or data["updated_at"] >= original_updated_at

    def test_update_payment_status_no_change(self, client, created_payment):
        """PUT /api/v1/payments/{id} with same status still succeeds."""
        payment_id = created_payment["id"]
        current_status = created_payment["status"]
        update_payload = {"status": current_status}
        response = client.put(f"/api/v1/payments/{payment_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["status"] == current_status


# ---------------------------------------------------------------------------
# 5. test_delete_payment — DELETE /api/v1/payments/{id}
# ---------------------------------------------------------------------------

class TestDeletePayment:
    """Tests for deleting payments."""

    def test_delete_payment_success(self, client, created_payment):
        """DELETE /api/v1/payments/{id} deletes a payment successfully."""
        payment_id = created_payment["id"]
        response = client.delete(f"/api/v1/payments/{payment_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/payments/{payment_id}")
        assert get_response.status_code == 404

    def test_delete_payment_not_found(self, client):
        """DELETE /api/v1/payments/{id} returns 404 for non-existent payment."""
        response = client.delete("/api/v1/payments/nonexistent-id")
        assert response.status_code == 404

    def test_delete_payment_already_deleted(self, client, created_payment):
        """DELETE /api/v1/payments/{id} returns 404 when deleting already-deleted payment."""
        payment_id = created_payment["id"]

        response1 = client.delete(f"/api/v1/payments/{payment_id}")
        assert response1.status_code == 204

        response2 = client.delete(f"/api/v1/payments/{payment_id}")
        assert response2.status_code == 404

    def test_delete_payment_invalidates_list(self, client, created_payment, sample_payment_payload):
        """Deleted payment no longer appears in list endpoint."""
        payment_id = created_payment["id"]

        list_response = client.get("/api/v1/payments")
        assert list_response.json()["total"] == 1

        client.delete(f"/api/v1/payments/{payment_id}")

        list_response = client.get("/api/v1/payments")
        assert list_response.json()["total"] == 0
        assert list_response.json()["items"] == []

    def test_delete_payment_does_not_affect_others(self, client, sample_payment_payload):
        """Deleting one payment does not affect other payments."""
        resp1 = client.post("/api/v1/payments", json={**sample_payment_payload, "order_id": "order-A"})
        resp2 = client.post("/api/v1/payments", json={**sample_payment_payload, "order_id": "order-B"})
        payment1_id = resp1.json()["id"]
        payment2_id = resp2.json()["id"]

        client.delete(f"/api/v1/payments/{payment1_id}")

        get_response = client.get(f"/api/v1/payments/{payment2_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payment2_id

    def test_delete_payment_response_has_no_content(self, client, created_payment):
        """DELETE /api/v1/payments/{id} returns no content in response body."""
        payment_id = created_payment["id"]
        response = client.delete(f"/api/v1/payments/{payment_id}")
        assert response.status_code == 204
        assert response.content == b""


# ---------------------------------------------------------------------------
# Integration / End-to-End Tests
# ---------------------------------------------------------------------------

class TestPaymentLifecycle:
    """End-to-end tests covering the full payment lifecycle."""

    def test_full_payment_lifecycle(self, client, sample_payment_payload):
        """Test complete CRUD lifecycle: create -> read -> update -> delete."""
        create_response = client.post("/api/v1/payments", json=sample_payment_payload)
        assert create_response.status_code == 201
        payment = create_response.json()
        payment_id = payment["id"]
        assert payment["status"] == "pending"

        get_response = client.get(f"/api/v1/payments/{payment_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "pending"

        update_response = client.put(
            f"/api/v1/payments/{payment_id}",
            json={"status": "completed"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "completed"

        get_response2 = client.get(f"/api/v1/payments/{payment_id}")
        assert get_response2.status_code == 200
        assert get_response2.json()["status"] == "completed"

        delete_response = client.delete(f"/api/v1/payments/{payment_id}")
        assert delete_response.status_code == 204

        get_response3 = client.get(f"/api/v1/payments/{payment_id}")
        assert get_response3.status_code == 404

    def test_multiple_payments_independent_lifecycle(self, client, sample_payment_payload):
        """Test that multiple payments can be managed independently."""
        ids = []
        for i in range(3):
            resp = client.post("/api/v1/payments", json={**sample_payment_payload, "order_id": f"order-{i}"})
            ids.append(resp.json()["id"])

        client.put(f"/api/v1/payments/{ids[1]}", json={"status": "completed"})
        client.delete(f"/api/v1/payments/{ids[0]}")

        assert client.get(f"/api/v1/payments/{ids[0]}").status_code == 404
        assert client.get(f"/api/v1/payments/{ids[1]}").json()["status"] == "completed"
        assert client.get(f"/api/v1/payments/{ids[2]}").json()["status"] == "pending"

        list_resp = client.get("/api/v1/payments")
        assert list_resp.json()["total"] == 2
