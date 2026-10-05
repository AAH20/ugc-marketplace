"""
Comprehensive API tests for the Transactions endpoints.

Endpoints under test:
  - GET    /api/v1/transactions        — list transactions with pagination
  - POST   /api/v1/transactions        — create a new transaction
  - GET    /api/v1/transactions/{id}   — get a single transaction by ID
  - PUT    /api/v1/transactions/{id}   — update transaction status
  - DELETE /api/v1/transactions/{id}   — delete a transaction
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.api.transactions import (
    TransactionCreate,
    TransactionStatus,
    TransactionType,
    TransactionUpdate,
    router as transactions_router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app() -> FastAPI:
    """Create a minimal FastAPI app with the transactions router."""
    application = FastAPI(title="Test UGC Marketplace")
    application.include_router(transactions_router)
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Return a TestClient bound to the test app."""
    return TestClient(app)


@pytest.fixture()
def sample_transaction_payload() -> dict:
    """Return a valid payload for creating a transaction."""
    return {
        "buyer_id": str(uuid4()),
        "seller_id": str(uuid4()),
        "amount": 29.99,
        "currency": "USD",
        "type": "purchase",
        "description": "Test purchase",
    }


@pytest.fixture()
def created_transaction(
    client: TestClient, sample_transaction_payload: dict
) -> dict:
    """Create a transaction via the API and return the response body."""
    response = client.post("/api/v1/transactions", json=sample_transaction_payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# 1. GET /api/v1/transactions  — test_list_transactions
# ---------------------------------------------------------------------------


class TestListTransactions:
    """Tests for GET /api/v1/transactions."""

    def test_list_transactions_empty(self, client: TestClient) -> None:
        """When no transactions exist the list is empty."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["pages"] == 1

    def test_list_transactions_returns_created(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """A previously created transaction appears in the list."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        body = response.json()
        ids = [t["id"] for t in body["items"]]
        assert created_transaction["id"] in ids

    def test_list_transactions_pagination(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Pagination parameters limit results correctly."""
        # Create 5 transactions
        for _ in range(5):
            client.post("/api/v1/transactions", json=sample_transaction_payload)

        # Request page 1 with page_size=2
        response = client.get(
            "/api/v1/transactions", params={"page": 1, "page_size": 2}
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["pages"] == 3

    def test_list_transactions_pagination_second_page(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """The second page returns different items than the first."""
        for _ in range(5):
            client.post("/api/v1/transactions", json=sample_transaction_payload)

        page1 = client.get(
            "/api/v1/transactions", params={"page": 1, "page_size": 2}
        ).json()
        page2 = client.get(
            "/api/v1/transactions", params={"page": 2, "page_size": 2}
        ).json()

        page1_ids = {t["id"] for t in page1["items"]}
        page2_ids = {t["id"] for t in page2["items"]}
        assert page1_ids.isdisjoint(page2_ids)
        assert len(page2["items"]) == 2

    def test_list_transactions_filter_by_status(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Filtering by status returns only matching transactions."""
        # Create a pending transaction
        resp = client.post("/api/v1/transactions", json=sample_transaction_payload)
        txn_id = resp.json()["id"]

        # Update it to completed
        client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed"},
        )

        # Filter by completed
        response = client.get(
            "/api/v1/transactions", params={"status": "completed"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "completed"

    def test_list_transactions_filter_by_type(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Filtering by type returns only matching transactions."""
        sample_transaction_payload["type"] = "sale"
        client.post("/api/v1/transactions", json=sample_transaction_payload)

        response = client.get(
            "/api/v1/transactions", params={"type": "sale"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "sale"

    def test_list_transactions_filter_by_buyer(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Filtering by buyer_id returns only that buyer's transactions."""
        buyer_id = str(uuid4())
        sample_transaction_payload["buyer_id"] = buyer_id
        client.post("/api/v1/transactions", json=sample_transaction_payload)

        response = client.get(
            "/api/v1/transactions", params={"buyer_id": buyer_id}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["buyer_id"] == buyer_id

    def test_list_transactions_filter_by_seller(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Filtering by seller_id returns only that seller's transactions."""
        seller_id = str(uuid4())
        sample_transaction_payload["seller_id"] = seller_id
        client.post("/api/v1/transactions", json=sample_transaction_payload)

        response = client.get(
            "/api/v1/transactions", params={"seller_id": seller_id}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["seller_id"] == seller_id

    def test_list_transactions_response_structure(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Each transaction in the list has the expected fields."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) > 0
        txn = body["items"][0]
        expected_keys = {
            "id",
            "buyer_id",
            "seller_id",
            "amount",
            "currency",
            "type",
            "status",
            "created_at",
        }
        assert expected_keys.issubset(txn.keys())

    def test_list_transactions_invalid_page(
        self, client: TestClient
    ) -> None:
        """Page number below 1 returns 422."""
        response = client.get("/api/v1/transactions", params={"page": 0})
        assert response.status_code == 422

    def test_list_transactions_invalid_page_size(
        self, client: TestClient
    ) -> None:
        """Page size above 100 returns 422."""
        response = client.get(
            "/api/v1/transactions", params={"page_size": 101}
        )
        assert response.status_code == 422

    def test_list_transactions_content_type(
        self, client: TestClient
    ) -> None:
        """The response has application/json content type."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 2. POST /api/v1/transactions  — test_create_transaction
# ---------------------------------------------------------------------------


class TestCreateTransaction:
    """Tests for POST /api/v1/transactions."""

    def test_create_transaction_success(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """A valid payload returns 201 and the created transaction."""
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert body["buyer_id"] == sample_transaction_payload["buyer_id"]
        assert body["seller_id"] == sample_transaction_payload["seller_id"]
        assert body["amount"] == sample_transaction_payload["amount"]
        assert body["currency"] == sample_transaction_payload["currency"]
        assert body["type"] == sample_transaction_payload["type"]
        assert body["status"] == "pending"
        assert "created_at" in body

    def test_create_transaction_auto_generates_id(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """The server assigns a unique id when none is provided."""
        resp1 = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        resp2 = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_transaction_default_currency(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Currency defaults to USD when omitted."""
        del sample_transaction_payload["currency"]
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 201
        assert response.json()["currency"] == "USD"

    def test_create_transaction_default_status(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Status defaults to pending on creation."""
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_create_transaction_missing_buyer_id(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Missing buyer_id returns 422."""
        del sample_transaction_payload["buyer_id"]
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_missing_seller_id(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Missing seller_id returns 422."""
        del sample_transaction_payload["seller_id"]
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_missing_amount(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Missing amount returns 422."""
        del sample_transaction_payload["amount"]
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_missing_type(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Missing type returns 422."""
        del sample_transaction_payload["type"]
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_invalid_amount_type(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """A non-numeric amount returns 422."""
        sample_transaction_payload["amount"] = "not-a-number"
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_negative_amount(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """A negative amount is rejected with 422."""
        sample_transaction_payload["amount"] = -10.00
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_zero_amount(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """A zero amount is rejected with 422."""
        sample_transaction_payload["amount"] = 0
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_invalid_currency(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """An invalid currency code returns 422."""
        sample_transaction_payload["currency"] = "INVALID"
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_invalid_type(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """An invalid transaction type returns 422."""
        sample_transaction_payload["type"] = "invalid_type"
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_invalid_buyer_id(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """A non-UUID buyer_id returns 422."""
        sample_transaction_payload["buyer_id"] = "not-a-uuid"
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 422

    def test_create_transaction_with_metadata(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Metadata is stored and returned."""
        sample_transaction_payload["metadata"] = {"order_id": "ord-123"}
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 201
        assert response.json()["metadata"] == {"order_id": "ord-123"}

    def test_create_transaction_with_description(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """Description is stored and returned."""
        sample_transaction_payload["description"] = "A detailed description"
        response = client.post(
            "/api/v1/transactions", json=sample_transaction_payload
        )
        assert response.status_code == 201
        assert response.json()["description"] == "A detailed description"

    def test_create_transaction_empty_body(
        self, client: TestClient
    ) -> None:
        """An empty JSON body returns 422."""
        response = client.post("/api/v1/transactions", json={})
        assert response.status_code == 422

    def test_create_transaction_no_body(
        self, client: TestClient
    ) -> None:
        """Sending no body at all returns 422."""
        response = client.post("/api/v1/transactions")
        assert response.status_code == 422

    def test_create_transaction_content_type(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """The response has application/json content type."""
        response = client.post(
            "/api/v1/transactions",
            json=sample_transaction_payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")

    def test_create_transaction_all_types(
        self, client: TestClient, sample_transaction_payload: dict
    ) -> None:
        """All valid transaction types are accepted."""
        for txn_type in TransactionType:
            sample_transaction_payload["type"] = txn_type.value
            response = client.post(
                "/api/v1/transactions", json=sample_transaction_payload
            )
            assert response.status_code == 201
            assert response.json()["type"] == txn_type.value


# ---------------------------------------------------------------------------
# 3. GET /api/v1/transactions/{id}  — test_get_transaction
# ---------------------------------------------------------------------------


class TestGetTransaction:
    """Tests for GET /api/v1/transactions/{id}."""

    def test_get_transaction_success(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Getting a valid transaction returns 200 and the transaction."""
        txn_id = created_transaction["id"]
        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == txn_id
        assert body["buyer_id"] == created_transaction["buyer_id"]
        assert body["seller_id"] == created_transaction["seller_id"]
        assert body["amount"] == created_transaction["amount"]
        assert body["currency"] == created_transaction["currency"]
        assert body["type"] == created_transaction["type"]
        assert body["status"] == created_transaction["status"]

    def test_get_transaction_not_found(self, client: TestClient) -> None:
        """Getting a non-existent transaction returns 404."""
        response = client.get(f"/api/v1/transactions/{uuid4()}")
        assert response.status_code == 404

    def test_get_transaction_invalid_id(self, client: TestClient) -> None:
        """An invalid UUID format returns 422."""
        response = client.get("/api/v1/transactions/not-a-uuid")
        assert response.status_code == 422

    def test_get_transaction_response_structure(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """The response has all expected fields."""
        txn_id = created_transaction["id"]
        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 200
        body = response.json()
        expected_keys = {
            "id",
            "buyer_id",
            "seller_id",
            "amount",
            "currency",
            "type",
            "status",
            "description",
            "metadata",
            "created_at",
            "updated_at",
        }
        assert expected_keys.issubset(body.keys())

    def test_get_transaction_content_type(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """The response has application/json content type."""
        txn_id = created_transaction["id"]
        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_transaction_after_update(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Getting a transaction after update reflects the new status."""
        txn_id = created_transaction["id"]
        client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed"},
        )
        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# 4. PUT /api/v1/transactions/{id}  — test_update_transaction_status
# ---------------------------------------------------------------------------


class TestUpdateTransactionStatus:
    """Tests for PUT /api/v1/transactions/{id}."""

    def test_update_transaction_status_success(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Updating status returns 200 and the updated transaction."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == txn_id
        assert body["status"] == "completed"
        assert body["updated_at"] is not None

    def test_update_transaction_status_all_valid(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """All valid statuses can be set."""
        txn_id = created_transaction["id"]
        for status in TransactionStatus:
            response = client.put(
                f"/api/v1/transactions/{txn_id}",
                json={"status": status.value},
            )
            assert response.status_code == 200
            assert response.json()["status"] == status.value

    def test_update_transaction_not_found(self, client: TestClient) -> None:
        """Updating a non-existent transaction returns 404."""
        response = client.put(
            f"/api/v1/transactions/{uuid4()}",
            json={"status": "completed"},
        )
        assert response.status_code == 404

    def test_update_transaction_invalid_id(self, client: TestClient) -> None:
        """An invalid UUID format returns 422."""
        response = client.put(
            "/api/v1/transactions/not-a-uuid",
            json={"status": "completed"},
        )
        assert response.status_code == 422

    def test_update_transaction_invalid_status(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """An invalid status value returns 422."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "invalid_status"},
        )
        assert response.status_code == 422

    def test_update_transaction_missing_status(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Missing status field returns 422."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={},
        )
        assert response.status_code == 422

    def test_update_transaction_description(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Description can be updated."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed", "description": "Updated description"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"

    def test_update_transaction_metadata(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Metadata can be updated."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed", "metadata": {"key": "value"}},
        )
        assert response.status_code == 200
        assert response.json()["metadata"] == {"key": "value"}

    def test_update_transaction_reflects_in_get(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """After update, GET returns the updated transaction."""
        txn_id = created_transaction["id"]
        client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "refunded"},
        )
        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "refunded"

    def test_update_transaction_content_type(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """The response has application/json content type."""
        txn_id = created_transaction["id"]
        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"status": "completed"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 5. DELETE /api/v1/transactions/{id}  — test_delete_transaction
# ---------------------------------------------------------------------------


class TestDeleteTransaction:
    """Tests for DELETE /api/v1/transactions/{id}."""

    def test_delete_transaction_success(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Deleting a valid transaction returns 204."""
        txn_id = created_transaction["id"]
        response = client.delete(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 204

    def test_delete_transaction_removes_it(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """After deletion, the transaction is no longer accessible."""
        txn_id = created_transaction["id"]
        client.delete(f"/api/v1/transactions/{txn_id}")

        response = client.get(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 404

    def test_delete_transaction_not_found(self, client: TestClient) -> None:
        """Deleting a non-existent transaction returns 404."""
        response = client.delete(f"/api/v1/transactions/{uuid4()}")
        assert response.status_code == 404

    def test_delete_transaction_invalid_id(self, client: TestClient) -> None:
        """An invalid UUID format returns 422."""
        response = client.delete("/api/v1/transactions/not-a-uuid")
        assert response.status_code == 422

    def test_delete_transaction_idempotent_behavior(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """Deleting the same transaction twice returns 404 on the second call."""
        txn_id = created_transaction["id"]
        resp1 = client.delete(f"/api/v1/transactions/{txn_id}")
        assert resp1.status_code == 204

        resp2 = client.delete(f"/api/v1/transactions/{txn_id}")
        assert resp2.status_code == 404

    def test_delete_transaction_not_in_list(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """After deletion, the transaction no longer appears in the list."""
        txn_id = created_transaction["id"]
        client.delete(f"/api/v1/transactions/{txn_id}")

        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        body = response.json()
        ids = [t["id"] for t in body["items"]]
        assert txn_id not in ids

    def test_delete_transaction_empty_response_body(
        self, client: TestClient, created_transaction: dict
    ) -> None:
        """The delete response has no body."""
        txn_id = created_transaction["id"]
        response = client.delete(f"/api/v1/transactions/{txn_id}")
        assert response.status_code == 204
        assert response.content == b""
