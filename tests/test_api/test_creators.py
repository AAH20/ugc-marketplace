"""
Comprehensive API tests for the Creators endpoints.

Endpoints under test:
  - GET    /api/v1/creators        — list creators with pagination and filtering
  - POST   /api/v1/creators        — create a new creator
  - GET    /api/v1/creators/{id}   — get a single creator by ID
  - PUT    /api/v1/creators/{id}   — update a creator
  - DELETE /api/v1/creators/{id}   — delete a creator
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.api.creators import router as creators_router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app() -> FastAPI:
    """Create a minimal FastAPI app with the creators router."""
    application = FastAPI(title="Test UGC Marketplace — Creators")
    application.include_router(creators_router, prefix="/api/v1")
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Return a TestClient bound to the test app."""
    return TestClient(app)


@pytest.fixture()
def sample_creator_payload() -> dict:
    """Return a valid payload for creating a creator."""
    return {
        "name": "Test Creator",
        "email": "test.creator@example.com",
        "handle": "@testcreator",
        "tier": "bronze",
        "bio": "A test creator for API testing.",
        "categories": ["tech", "reviews"],
    }


@pytest.fixture()
def created_creator(client: TestClient, sample_creator_payload: dict) -> dict:
    """Create a creator via the API and return the response body."""
    response = client.post("/api/v1/creators", json=sample_creator_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def multiple_creators(client: TestClient) -> list[dict]:
    """Create multiple creators for pagination and filtering tests."""
    creators = []
    for i in range(5):
        payload = {
            "name": f"Creator {i}",
            "email": f"creator{i}@example.com",
            "handle": f"@creator{i}",
            "tier": ["bronze", "silver", "gold", "platinum", "bronze"][i],
            "status": "active",
            "bio": f"Bio for creator {i}",
            "categories": ["tech"] if i % 2 == 0 else ["lifestyle"],
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 201
        creators.append(response.json())
    return creators


# ---------------------------------------------------------------------------
# 1. GET /api/v1/creators  — test_list_creators
# ---------------------------------------------------------------------------


class TestListCreators:
    """Tests for GET /api/v1/creators."""

    def test_list_creators_empty(self, client: TestClient) -> None:
        """When no creators exist the list is empty."""
        response = client.get("/api/v1/creators")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 10
        assert body["total_pages"] == 1

    def test_list_creators_returns_created(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """A previously created creator appears in the list."""
        response = client.get("/api/v1/creators")
        assert response.status_code == 200
        body = response.json()
        ids = [c["id"] for c in body["data"]]
        assert created_creator["id"] in ids

    def test_list_creators_pagination_first_page(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """First page returns correct items and metadata."""
        response = client.get("/api/v1/creators", params={"page": 1, "page_size": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["total"] == 5
        assert body["total_pages"] == 3
        assert len(body["data"]) == 2

    def test_list_creators_pagination_second_page(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Second page returns different items than the first."""
        page1 = client.get(
            "/api/v1/creators", params={"page": 1, "page_size": 2}
        ).json()
        page2 = client.get(
            "/api/v1/creators", params={"page": 2, "page_size": 2}
        ).json()

        page1_ids = {c["id"] for c in page1["data"]}
        page2_ids = {c["id"] for c in page2["data"]}
        assert page1_ids.isdisjoint(page2_ids)
        assert len(page2["data"]) == 2

    def test_list_creators_pagination_last_partial_page(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Last page returns remaining items when total is not evenly divisible."""
        response = client.get("/api/v1/creators", params={"page": 3, "page_size": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 3
        assert len(body["data"]) == 1  # 5 total, 2 per page -> last page has 1

    def test_list_creators_pagination_beyond_last_page(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Requesting a page beyond the last returns empty data."""
        response = client.get("/api/v1/creators", params={"page": 10, "page_size": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["total"] == 5

    def test_list_creators_invalid_page_number(self, client: TestClient) -> None:
        """Page number below 1 returns 422."""
        response = client.get("/api/v1/creators", params={"page": 0})
        assert response.status_code == 422

    def test_list_creators_invalid_page_size(self, client: TestClient) -> None:
        """Page size of 0 returns 422."""
        response = client.get("/api/v1/creators", params={"page_size": 0})
        assert response.status_code == 422

    def test_list_creators_page_size_too_large(self, client: TestClient) -> None:
        """Page size above 100 returns 422."""
        response = client.get("/api/v1/creators", params={"page_size": 101})
        assert response.status_code == 422

    def test_list_creators_filter_by_tier(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Filtering by tier returns only matching creators."""
        response = client.get("/api/v1/creators", params={"tier": "bronze"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2  # creators 0 and 4 are bronze
        for creator in body["data"]:
            assert creator["tier"] == "bronze"

    def test_list_creators_filter_by_status(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Filtering by status returns only matching creators."""
        # Update one creator to suspended
        creator_id = multiple_creators[0]["id"]
        client.put(f"/api/v1/creators/{creator_id}", json={"status": "suspended"})

        response = client.get("/api/v1/creators", params={"status": "suspended"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["status"] == "suspended"

    def test_list_creators_search_by_name(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Search by name returns matching creators."""
        response = client.get("/api/v1/creators", params={"search": "Creator 1"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert "Creator 1" in body["data"][0]["name"]

    def test_list_creators_search_by_handle(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Search by handle returns matching creators."""
        response = client.get("/api/v1/creators", params={"search": "@creator2"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["handle"] == "@creator2"

    def test_list_creators_search_case_insensitive(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Search is case-insensitive."""
        response = client.get("/api/v1/creators", params={"search": "creator 1"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1

    def test_list_creators_search_no_results(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Search with no matches returns empty list."""
        response = client.get("/api/v1/creators", params={"search": "zzzznonexistent"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["total"] == 0

    def test_list_creators_combined_filters(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Multiple filters can be combined."""
        response = client.get(
            "/api/v1/creators",
            params={"tier": "bronze", "search": "Creator 0"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["name"] == "Creator 0"

    def test_list_creators_response_structure(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Each creator in the list has the expected fields."""
        response = client.get("/api/v1/creators")
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) > 0
        creator = body["data"][0]
        expected_keys = {
            "id",
            "name",
            "email",
            "handle",
            "tier",
            "status",
            "bio",
            "followers",
            "engagement_rate",
            "categories",
            "joined_at",
            "verified",
        }
        assert expected_keys.issubset(creator.keys())

    def test_list_creators_content_type(self, client: TestClient) -> None:
        """The response has application/json content type."""
        response = client.get("/api/v1/creators")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 2. POST /api/v1/creators  — test_create_creator
# ---------------------------------------------------------------------------


class TestCreateCreator:
    """Tests for POST /api/v1/creators."""

    def test_create_creator_success(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """A valid payload returns 201 and the created creator."""
        response = client.post("/api/v1/creators", json=sample_creator_payload)
        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert body["name"] == sample_creator_payload["name"]
        assert body["email"] == sample_creator_payload["email"]
        assert body["handle"] == sample_creator_payload["handle"]
        assert body["tier"] == sample_creator_payload["tier"]
        assert body["bio"] == sample_creator_payload["bio"]
        assert body["categories"] == sample_creator_payload["categories"]
        assert body["status"] == "pending"
        assert body["followers"] == 0
        assert body["engagement_rate"] == 0.0
        assert body["verified"] is False
        assert "joined_at" in body

    def test_create_creator_minimal_payload(self, client: TestClient) -> None:
        """Only required fields are needed to create a creator."""
        payload = {"name": "Minimal Creator", "email": "min@example.com", "handle": "@mincreator"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Minimal Creator"
        assert body["tier"] == "bronze"  # default
        assert body["status"] == "pending"  # default

    def test_create_creator_generates_unique_ids(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """Each creation returns a distinct id."""
        resp1 = client.post("/api/v1/creators", json=sample_creator_payload)
        resp2 = client.post(
            "/api/v1/creators",
            json={**sample_creator_payload, "email": "other@example.com", "handle": "@other"},
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_creator_missing_name(self, client: TestClient) -> None:
        """Missing required 'name' field returns 422."""
        payload = {"email": "noname@example.com", "handle": "@noname"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_missing_email(self, client: TestClient) -> None:
        """Missing required 'email' field returns 422."""
        payload = {"name": "No Email", "handle": "@noemail"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_missing_handle(self, client: TestClient) -> None:
        """Missing required 'handle' field returns 422."""
        payload = {"name": "No Handle", "email": "nohandle@example.com"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_empty_name(self, client: TestClient) -> None:
        """An empty string for 'name' returns 422."""
        payload = {"name": "", "email": "empty@example.com", "handle": "@empty"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_short_name(self, client: TestClient) -> None:
        """A name shorter than 2 characters returns 422."""
        payload = {"name": "A", "email": "short@example.com", "handle": "@short"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_long_name(self, client: TestClient) -> None:
        """A name longer than 100 characters returns 422."""
        payload = {"name": "A" * 101, "email": "long@example.com", "handle": "@long"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_invalid_email(self, client: TestClient) -> None:
        """A malformed email address returns 422."""
        payload = {"name": "Bad Email", "email": "not-an-email", "handle": "@bad"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_invalid_handle_no_at(self, client: TestClient) -> None:
        """A handle not starting with @ returns 422."""
        payload = {"name": "No At", "email": "noat@example.com", "handle": "noat"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_invalid_handle_special_chars(self, client: TestClient) -> None:
        """A handle with special characters returns 422."""
        payload = {"name": "Special", "email": "special@example.com", "handle": "@spec!al"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_short_handle(self, client: TestClient) -> None:
        """A handle shorter than 3 characters returns 422."""
        payload = {"name": "Short Handle", "email": "sh@example.com", "handle": "@a"}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_long_handle(self, client: TestClient) -> None:
        """A handle longer than 30 characters returns 422."""
        payload = {"name": "Long Handle", "email": "lh@example.com", "handle": "@" + "a" * 30}
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_invalid_tier(self, client: TestClient) -> None:
        """An invalid tier value returns 422."""
        payload = {
            "name": "Bad Tier",
            "email": "badtier@example.com",
            "handle": "@badtier",
            "tier": "diamond",
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_all_valid_tiers(self, client: TestClient) -> None:
        """All valid tier values are accepted."""
        for tier in ("bronze", "silver", "gold", "platinum"):
            payload = {
                "name": f"Tier {tier}",
                "email": f"{tier}@example.com",
                "handle": f"@{tier}",
                "tier": tier,
            }
            response = client.post("/api/v1/creators", json=payload)
            assert response.status_code == 201
            assert response.json()["tier"] == tier

    def test_create_creator_duplicate_email(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """Creating two creators with the same email returns 409."""
        resp1 = client.post("/api/v1/creators", json=sample_creator_payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/creators", json=sample_creator_payload)
        assert resp2.status_code == 409

    def test_create_creator_duplicate_handle(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """Creating two creators with the same handle returns 409."""
        resp1 = client.post("/api/v1/creators", json=sample_creator_payload)
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/v1/creators",
            json={**sample_creator_payload, "email": "different@example.com"},
        )
        assert resp2.status_code == 409

    def test_create_creator_duplicate_handle_case_insensitive(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """Handle uniqueness check is case-insensitive."""
        resp1 = client.post("/api/v1/creators", json=sample_creator_payload)
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/v1/creators",
            json={
                **sample_creator_payload,
                "email": "different@example.com",
                "handle": "@TESTCREATOR",
            },
        )
        assert resp2.status_code == 409

    def test_create_creator_empty_body(self, client: TestClient) -> None:
        """An empty JSON body returns 422."""
        response = client.post("/api/v1/creators", json={})
        assert response.status_code == 422

    def test_create_creator_no_body(self, client: TestClient) -> None:
        """Sending no body at all returns 422."""
        response = client.post("/api/v1/creators")
        assert response.status_code == 422

    def test_create_creator_content_type(
        self, client: TestClient, sample_creator_payload: dict
    ) -> None:
        """The response has application/json content type."""
        response = client.post("/api/v1/creators", json=sample_creator_payload)
        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")

    def test_create_creator_with_bio(self, client: TestClient) -> None:
        """Bio field is stored and returned."""
        payload = {
            "name": "Bio Creator",
            "email": "bio@example.com",
            "handle": "@bio",
            "bio": "A detailed bio.",
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 201
        assert response.json()["bio"] == "A detailed bio."

    def test_create_creator_with_categories(self, client: TestClient) -> None:
        """Categories are stored and returned."""
        payload = {
            "name": "Cat Creator",
            "email": "cat@example.com",
            "handle": "@cat",
            "categories": ["tech", "gaming", "reviews"],
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 201
        assert response.json()["categories"] == ["tech", "gaming", "reviews"]

    def test_create_creator_duplicate_categories(self, client: TestClient) -> None:
        """Duplicate categories in the list return 422."""
        payload = {
            "name": "Dup Cat",
            "email": "dupcat@example.com",
            "handle": "@dupcat",
            "categories": ["tech", "tech"],
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_too_many_categories(self, client: TestClient) -> None:
        """More than 5 categories returns 422."""
        payload = {
            "name": "Many Cat",
            "email": "manycat@example.com",
            "handle": "@manycat",
            "categories": ["a", "b", "c", "d", "e", "f"],
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422

    def test_create_creator_long_bio(self, client: TestClient) -> None:
        """Bio longer than 500 characters returns 422."""
        payload = {
            "name": "Long Bio",
            "email": "longbio@example.com",
            "handle": "@longbio",
            "bio": "x" * 501,
        }
        response = client.post("/api/v1/creators", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 3. GET /api/v1/creators/{id}  — test_get_creator
# ---------------------------------------------------------------------------


class TestGetCreator:
    """Tests for GET /api/v1/creators/{id}."""

    def test_get_creator_success(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Getting a valid creator returns 200 and the creator."""
        creator_id = created_creator["id"]
        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == creator_id
        assert body["name"] == created_creator["name"]
        assert body["email"] == created_creator["email"]
        assert body["handle"] == created_creator["handle"]
        assert body["tier"] == created_creator["tier"]
        assert body["status"] == created_creator["status"]

    def test_get_creator_not_found(self, client: TestClient) -> None:
        """Getting a non-existent creator returns 404."""
        response = client.get("/api/v1/creators/nonexistent-id")
        assert response.status_code == 404

    def test_get_creator_response_structure(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """The response has all expected fields."""
        creator_id = created_creator["id"]
        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 200
        body = response.json()
        expected_keys = {
            "id",
            "name",
            "email",
            "handle",
            "tier",
            "status",
            "bio",
            "followers",
            "engagement_rate",
            "categories",
            "joined_at",
            "verified",
        }
        assert expected_keys.issubset(body.keys())

    def test_get_creator_content_type(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """The response has application/json content type."""
        creator_id = created_creator["id"]
        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_creator_after_update(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Getting a creator after update reflects the new data."""
        creator_id = created_creator["id"]
        client.put(f"/api/v1/creators/{creator_id}", json={"name": "Updated Name"})
        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_get_creator_does_not_leak_others(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Getting one creator does not return other creators."""
        target = multiple_creators[0]
        response = client.get(f"/api/v1/creators/{target['id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == target["id"]
        assert body["name"] == target["name"]


# ---------------------------------------------------------------------------
# 4. PUT /api/v1/creators/{id}  — test_update_creator
# ---------------------------------------------------------------------------


class TestUpdateCreator:
    """Tests for PUT /api/v1/creators/{id}."""

    def test_update_creator_success(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating a creator returns 200 and the updated creator."""
        creator_id = created_creator["id"]
        update_payload = {"name": "Updated Name", "tier": "gold"}
        response = client.put(f"/api/v1/creators/{creator_id}", json=update_payload)
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == creator_id
        assert body["name"] == "Updated Name"
        assert body["tier"] == "gold"
        # Unspecified fields should remain unchanged
        assert body["email"] == created_creator["email"]
        assert body["handle"] == created_creator["handle"]

    def test_update_creator_not_found(self, client: TestClient) -> None:
        """Updating a non-existent creator returns 404."""
        response = client.put(
            "/api/v1/creators/nonexistent-id", json={"name": "New Name"}
        )
        assert response.status_code == 404

    def test_update_creator_name(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Name can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"name": "New Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_update_creator_email(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Email can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"email": "newemail@example.com"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newemail@example.com"

    def test_update_creator_handle(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Handle can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"handle": "@newhandle"}
        )
        assert response.status_code == 200
        assert response.json()["handle"] == "@newhandle"

    def test_update_creator_tier(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Tier can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"tier": "platinum"}
        )
        assert response.status_code == 200
        assert response.json()["tier"] == "platinum"

    def test_update_creator_status(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Status can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"status": "active"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_update_creator_bio(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Bio can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"bio": "Updated bio."}
        )
        assert response.status_code == 200
        assert response.json()["bio"] == "Updated bio."

    def test_update_creator_categories(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Categories can be updated."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}",
            json={"categories": ["new", "categories"]},
        )
        assert response.status_code == 200
        assert response.json()["categories"] == ["new", "categories"]

    def test_update_creator_invalid_name(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating with an invalid name returns 422."""
        creator_id = created_creator["id"]
        response = client.put(f"/api/v1/creators/{creator_id}", json={"name": ""})
        assert response.status_code == 422

    def test_update_creator_invalid_email(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating with an invalid email returns 422."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"email": "not-an-email"}
        )
        assert response.status_code == 422

    def test_update_creator_invalid_tier(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating with an invalid tier returns 422."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"tier": "diamond"}
        )
        assert response.status_code == 422

    def test_update_creator_invalid_status(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating with an invalid status returns 422."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"status": "invalid_status"}
        )
        assert response.status_code == 422

    def test_update_creator_duplicate_email(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Updating to an email that another creator already has returns 409."""
        creator1_id = multiple_creators[0]["id"]
        creator2_email = multiple_creators[1]["email"]

        response = client.put(
            f"/api/v1/creators/{creator1_id}", json={"email": creator2_email}
        )
        assert response.status_code == 409

    def test_update_creator_duplicate_handle(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Updating to a handle that another creator already has returns 409."""
        creator1_id = multiple_creators[0]["id"]
        creator2_handle = multiple_creators[1]["handle"]

        response = client.put(
            f"/api/v1/creators/{creator1_id}", json={"handle": creator2_handle}
        )
        assert response.status_code == 409

    def test_update_creator_same_email_allowed(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating a creator with its own email is allowed (no false conflict)."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"email": created_creator["email"]}
        )
        assert response.status_code == 200

    def test_update_creator_same_handle_allowed(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating a creator with its own handle is allowed (no false conflict)."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"handle": created_creator["handle"]}
        )
        assert response.status_code == 200

    def test_update_creator_empty_body(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Updating with an empty body is a no-op success."""
        creator_id = created_creator["id"]
        response = client.put(f"/api/v1/creators/{creator_id}", json={})
        assert response.status_code == 200
        # Data should be unchanged
        assert response.json()["name"] == created_creator["name"]

    def test_update_creator_reflects_in_get(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """After update, GET returns the updated creator."""
        creator_id = created_creator["id"]
        client.put(f"/api/v1/creators/{creator_id}", json={"name": "Reflected Name"})
        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Reflected Name"

    def test_update_creator_content_type(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """The response has application/json content type."""
        creator_id = created_creator["id"]
        response = client.put(
            f"/api/v1/creators/{creator_id}", json={"name": "Content Type Test"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 5. DELETE /api/v1/creators/{id}  — test_delete_creator
# ---------------------------------------------------------------------------


class TestDeleteCreator:
    """Tests for DELETE /api/v1/creators/{id}."""

    def test_delete_creator_success(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Deleting a valid creator returns 204."""
        creator_id = created_creator["id"]
        response = client.delete(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 204

    def test_delete_creator_removes_it(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """After deletion, the creator is no longer accessible."""
        creator_id = created_creator["id"]
        client.delete(f"/api/v1/creators/{creator_id}")

        response = client.get(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 404

    def test_delete_creator_not_found(self, client: TestClient) -> None:
        """Deleting a non-existent creator returns 404."""
        response = client.delete("/api/v1/creators/nonexistent-id")
        assert response.status_code == 404

    def test_delete_creator_idempotent_behavior(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """Deleting the same creator twice returns 404 on the second call."""
        creator_id = created_creator["id"]
        resp1 = client.delete(f"/api/v1/creators/{creator_id}")
        assert resp1.status_code == 204

        resp2 = client.delete(f"/api/v1/creators/{creator_id}")
        assert resp2.status_code == 404

    def test_delete_creator_not_in_list(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """After deletion, the creator no longer appears in the list."""
        creator_id = created_creator["id"]
        client.delete(f"/api/v1/creators/{creator_id}")

        response = client.get("/api/v1/creators")
        assert response.status_code == 200
        body = response.json()
        ids = [c["id"] for c in body["data"]]
        assert creator_id not in ids

    def test_delete_creator_does_not_affect_others(
        self, client: TestClient, multiple_creators: list[dict]
    ) -> None:
        """Deleting one creator does not affect other creators."""
        to_delete = multiple_creators[0]
        to_keep = multiple_creators[1]

        client.delete(f"/api/v1/creators/{to_delete['id']}")

        response = client.get(f"/api/v1/creators/{to_keep['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == to_keep["id"]

    def test_delete_creator_empty_response_body(
        self, client: TestClient, created_creator: dict
    ) -> None:
        """The delete response has no body."""
        creator_id = created_creator["id"]
        response = client.delete(f"/api/v1/creators/{creator_id}")
        assert response.status_code == 204
        assert response.content == b""


# ---------------------------------------------------------------------------
# Integration / End-to-End Tests
# ---------------------------------------------------------------------------


class TestCreatorLifecycle:
    """End-to-end tests covering the full creator lifecycle."""

    def test_full_creator_lifecycle(self, client: TestClient) -> None:
        """Test complete CRUD lifecycle: create -> read -> update -> delete."""
        # Create
        create_response = client.post(
            "/api/v1/creators",
            json={
                "name": "Lifecycle Creator",
                "email": "lifecycle@example.com",
                "handle": "@lifecycle",
                "tier": "silver",
            },
        )
        assert create_response.status_code == 201
        creator = create_response.json()
        creator_id = creator["id"]
        assert creator["status"] == "pending"

        # Read
        get_response = client.get(f"/api/v1/creators/{creator_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "pending"

        # Update
        update_response = client.put(
            f"/api/v1/creators/{creator_id}",
            json={"status": "active", "tier": "gold"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "active"
        assert update_response.json()["tier"] == "gold"

        # Verify update persisted
        get_response2 = client.get(f"/api/v1/creators/{creator_id}")
        assert get_response2.status_code == 200
        assert get_response2.json()["status"] == "active"
        assert get_response2.json()["tier"] == "gold"

        # Delete
        delete_response = client.delete(f"/api/v1/creators/{creator_id}")
        assert delete_response.status_code == 204

        # Verify deletion
        get_response3 = client.get(f"/api/v1/creators/{creator_id}")
        assert get_response3.status_code == 404

    def test_multiple_creators_independent_lifecycle(self, client: TestClient) -> None:
        """Test that multiple creators can be managed independently."""
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/creators",
                json={
                    "name": f"Independent {i}",
                    "email": f"indep{i}@example.com",
                    "handle": f"@indep{i}",
                },
            )
            ids.append(resp.json()["id"])

        # Update second creator
        client.put(f"/api/v1/creators/{ids[1]}", json={"tier": "platinum"})

        # Delete first creator
        client.delete(f"/api/v1/creators/{ids[0]}")

        # Verify first is gone
        assert client.get(f"/api/v1/creators/{ids[0]}").status_code == 404

        # Verify second is updated
        assert client.get(f"/api/v1/creators/{ids[1]}").json()["tier"] == "platinum"

        # Verify third is unchanged
        assert client.get(f"/api/v1/creators/{ids[2]}").json()["tier"] == "bronze"

        # Verify list count
        list_resp = client.get("/api/v1/creators")
        assert list_resp.json()["total"] == 2
