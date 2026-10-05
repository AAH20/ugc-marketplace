"""
Comprehensive API tests for the Categories endpoints.

Tests cover:
- GET    /api/v1/categories        (list with pagination)
- POST   /api/v1/categories        (create)
- GET    /api/v1/categories/{id}   (retrieve)
- PUT    /api/v1/categories/{id}   (update)
- DELETE /api/v1/categories/{id}   (delete)
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to a minimal FastAPI app with the categories router.

    Loads the categories module directly from its file path to avoid
    the broken import in ugc_marketplace.api.__init__.
    """
    import importlib.util
    import sys
    from pathlib import Path

    # Load the categories module directly from file
    categories_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "ugc_marketplace"
        / "api"
        / "categories.py"
    )
    spec = importlib.util.spec_from_file_location("categories_module", categories_path)
    categories_module = importlib.util.module_from_spec(spec)
    sys.modules["categories_module"] = categories_module
    spec.loader.exec_module(categories_module)

    app = FastAPI()
    app.include_router(categories_module.router)
    return TestClient(app)


@pytest.fixture
def sample_category_payload() -> dict:
    """Return a valid payload for creating a category."""
    return {
        "name": "Test Category",
        "slug": "test-category",
        "description": "A test category for API testing",
        "parent_id": None,
        "icon": "🧪",
        "is_active": True,
        "sort_order": 100,
    }


@pytest.fixture
def created_category(client: TestClient, sample_category_payload: dict) -> dict:
    """Create a category via the API and return the response JSON."""
    response = client.post("/api/v1/categories", json=sample_category_payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# 1. GET /api/v1/categories  — test_list_categories
# ---------------------------------------------------------------------------


class TestListCategories:
    """Tests for the GET /api/v1/categories endpoint."""

    def test_list_categories_success(self, client: TestClient) -> None:
        """GET /api/v1/categories returns 200 with paginated structure."""
        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    def test_list_categories_default_pagination(self, client: TestClient) -> None:
        """Default pagination returns page 1 with 10 items per page."""
        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) <= 10

    def test_list_categories_custom_page_size(self, client: TestClient) -> None:
        """Custom page_size parameter limits the number of items returned."""
        response = client.get("/api/v1/categories", params={"page_size": 3})

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 3
        assert len(data["items"]) <= 3

    def test_list_categories_page_2(self, client: TestClient) -> None:
        """Page 2 returns different items than page 1."""
        resp1 = client.get("/api/v1/categories", params={"page": 1, "page_size": 5})
        resp2 = client.get("/api/v1/categories", params={"page": 2, "page_size": 5})

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        data1 = resp1.json()
        data2 = resp2.json()

        assert data1["page"] == 1
        assert data2["page"] == 2

        # If there are enough items, page 2 should have different items
        if data1["total"] > 5:
            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert ids1 != ids2

    def test_list_categories_total_pages_calculation(self, client: TestClient) -> None:
        """total_pages is calculated correctly based on total and page_size."""
        response = client.get("/api/v1/categories", params={"page_size": 5})

        assert response.status_code == 200
        data = response.json()

        expected_pages = (data["total"] + 4) // 5 if data["total"] > 0 else 1
        assert data["total_pages"] == expected_pages

    def test_list_categories_filter_by_search(self, client: TestClient) -> None:
        """Search filter returns only matching categories."""
        response = client.get("/api/v1/categories", params={"search": "digital"})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert "digital" in item["name"].lower() or "digital" in item["slug"].lower()

    def test_list_categories_filter_by_is_active_true(self, client: TestClient) -> None:
        """Filter by is_active=True returns only active categories."""
        response = client.get("/api/v1/categories", params={"is_active": True})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

    def test_list_categories_filter_by_is_active_false(self, client: TestClient) -> None:
        """Filter by is_active=False returns only inactive categories."""
        response = client.get("/api/v1/categories", params={"is_active": False})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is False

    def test_list_categories_filter_by_parent_id(self, client: TestClient) -> None:
        """Filter by parent_id returns only child categories."""
        # First get a category that has children (parent_id=2 has children in mock data)
        response = client.get("/api/v1/categories", params={"parent_id": 2})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["parent_id"] == 2

    def test_list_categories_invalid_page_number(self, client: TestClient) -> None:
        """Page number below 1 returns 422."""
        response = client.get("/api/v1/categories", params={"page": 0})

        assert response.status_code == 422

    def test_list_categories_invalid_page_size(self, client: TestClient) -> None:
        """Page size above 100 returns 422."""
        response = client.get("/api/v1/categories", params={"page_size": 101})

        assert response.status_code == 422

    def test_list_categories_page_size_zero(self, client: TestClient) -> None:
        """Page size of 0 returns 422."""
        response = client.get("/api/v1/categories", params={"page_size": 0})

        assert response.status_code == 422

    def test_list_categories_response_structure(self, client: TestClient) -> None:
        """Each category in the list has the expected fields."""
        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0

        category = data["items"][0]
        expected_keys = {
            "id",
            "name",
            "slug",
            "description",
            "parent_id",
            "icon",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
            "product_count",
        }
        assert expected_keys.issubset(category.keys())

    def test_list_categories_sorted_by_sort_order(self, client: TestClient) -> None:
        """Categories are sorted by sort_order ascending, then by name."""
        response = client.get("/api/v1/categories", params={"page_size": 100})

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        for i in range(len(items) - 1):
            current = (items[i]["sort_order"], items[i]["name"])
            next_item = (items[i + 1]["sort_order"], items[i + 1]["name"])
            assert current <= next_item

    def test_list_categories_content_type(self, client: TestClient) -> None:
        """Response Content-Type is application/json."""
        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_list_categories_total_matches_items(self, client: TestClient) -> None:
        """Total count is consistent with the number of items across pages."""
        response = client.get("/api/v1/categories", params={"page_size": 100})

        assert response.status_code == 200
        data = response.json()
        # total should be >= len(items) since we might have more pages
        assert data["total"] >= len(data["items"])


# ---------------------------------------------------------------------------
# 2. POST /api/v1/categories  — test_create_category
# ---------------------------------------------------------------------------


class TestCreateCategory:
    """Tests for the POST /api/v1/categories endpoint."""

    def test_create_category_success(
        self, client: TestClient, sample_category_payload: dict
    ) -> None:
        """Creating a category with valid data returns 201 and the category."""
        response = client.post("/api/v1/categories", json=sample_category_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_category_payload["name"]
        assert data["slug"] == sample_category_payload["slug"]
        assert data["description"] == sample_category_payload["description"]
        assert data["parent_id"] == sample_category_payload["parent_id"]
        assert data["icon"] == sample_category_payload["icon"]
        assert data["is_active"] == sample_category_payload["is_active"]
        assert data["sort_order"] == sample_category_payload["sort_order"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["product_count"] == 0

    def test_create_category_minimal_fields(self, client: TestClient) -> None:
        """Creating a category with only required fields succeeds."""
        payload = {"name": "Minimal", "slug": "minimal"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal"
        assert data["slug"] == "minimal"
        assert data["is_active"] is True
        assert data["sort_order"] == 0

    def test_create_category_missing_name(self, client: TestClient) -> None:
        """Missing required field 'name' returns 422."""
        payload = {"slug": "no-name"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_missing_slug(self, client: TestClient) -> None:
        """Missing required field 'slug' returns 422."""
        payload = {"name": "No Slug"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_empty_name(self, client: TestClient) -> None:
        """Empty string for 'name' returns 422."""
        payload = {"name": "", "slug": "empty-name"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_empty_slug(self, client: TestClient) -> None:
        """Empty string for 'slug' returns 422."""
        payload = {"name": "Empty Slug", "slug": ""}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_invalid_slug_format(self, client: TestClient) -> None:
        """Slug with invalid characters returns 422."""
        payload = {"name": "Invalid Slug", "slug": "Invalid_Slug_With_Underscores"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_slug_with_uppercase(self, client: TestClient) -> None:
        """Slug with uppercase letters returns 422."""
        payload = {"name": "Uppercase Slug", "slug": "UpperCaseSlug"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_duplicate_slug(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Creating a category with a duplicate slug returns 409."""
        payload = {
            "name": "Duplicate Slug Category",
            "slug": created_category["slug"],
        }
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 409

    def test_create_category_with_valid_parent_id(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Creating a subcategory with a valid parent_id succeeds."""
        payload = {
            "name": "Subcategory",
            "slug": "subcategory",
            "parent_id": created_category["id"],
        }
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["parent_id"] == created_category["id"]

    def test_create_category_with_invalid_parent_id(self, client: TestClient) -> None:
        """Creating a category with a non-existent parent_id returns 400."""
        payload = {
            "name": "Orphan Category",
            "slug": "orphan-category",
            "parent_id": 999999,
        }
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 400

    def test_create_category_name_too_long(self, client: TestClient) -> None:
        """Name exceeding 100 characters returns 422."""
        payload = {"name": "A" * 101, "slug": "too-long-name"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_slug_too_long(self, client: TestClient) -> None:
        """Slug exceeding 120 characters returns 422."""
        payload = {"name": "Too Long Slug", "slug": "a" * 121}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_description_too_long(self, client: TestClient) -> None:
        """Description exceeding 500 characters returns 422."""
        payload = {
            "name": "Too Long Description",
            "slug": "too-long-desc",
            "description": "A" * 501,
        }
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_sort_order_negative(self, client: TestClient) -> None:
        """Negative sort_order returns 422."""
        payload = {"name": "Negative Sort", "slug": "negative-sort", "sort_order": -1}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_sort_order_too_large(self, client: TestClient) -> None:
        """sort_order above 9999 returns 422."""
        payload = {"name": "Large Sort", "slug": "large-sort", "sort_order": 10000}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 422

    def test_create_category_empty_body(self, client: TestClient) -> None:
        """Empty JSON body returns 422."""
        response = client.post("/api/v1/categories", json={})

        assert response.status_code == 422

    def test_create_category_no_body(self, client: TestClient) -> None:
        """No body at all returns 422."""
        response = client.post("/api/v1/categories")

        assert response.status_code == 422

    def test_create_category_returns_unique_ids(
        self, client: TestClient, sample_category_payload: dict
    ) -> None:
        """Each POST returns a distinct category ID."""
        payload1 = {**sample_category_payload, "slug": "unique-slug-1"}
        payload2 = {**sample_category_payload, "slug": "unique-slug-2"}

        resp1 = client.post("/api/v1/categories", json=payload1)
        resp2 = client.post("/api/v1/categories", json=payload2)

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_category_content_type(
        self, client: TestClient, sample_category_payload: dict
    ) -> None:
        """Response Content-Type is application/json."""
        response = client.post("/api/v1/categories", json=sample_category_payload)

        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")

    def test_create_category_with_icon_emoji(self, client: TestClient) -> None:
        """Icon field accepts emoji characters."""
        payload = {"name": "Emoji Icon", "slug": "emoji-icon", "icon": "🎉"}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201
        assert response.json()["icon"] == "🎉"

    def test_create_category_with_icon_url(self, client: TestClient) -> None:
        """Icon field accepts URL strings."""
        payload = {
            "name": "URL Icon",
            "slug": "url-icon",
            "icon": "https://example.com/icon.png",
        }
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201
        assert response.json()["icon"] == "https://example.com/icon.png"

    def test_create_category_is_active_false(self, client: TestClient) -> None:
        """Creating an inactive category succeeds."""
        payload = {"name": "Inactive", "slug": "inactive", "is_active": False}
        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201
        assert response.json()["is_active"] is False


# ---------------------------------------------------------------------------
# 3. GET /api/v1/categories/{id}  — test_get_category
# ---------------------------------------------------------------------------


class TestGetCategory:
    """Tests for the GET /api/v1/categories/{id} endpoint."""

    def test_get_category_success(self, client: TestClient, created_category: dict) -> None:
        """GET /api/v1/categories/{id} returns the matching category."""
        category_id = created_category["id"]
        response = client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == created_category["name"]
        assert data["slug"] == created_category["slug"]
        assert data["description"] == created_category["description"]
        assert data["parent_id"] == created_category["parent_id"]
        assert data["icon"] == created_category["icon"]
        assert data["is_active"] == created_category["is_active"]
        assert data["sort_order"] == created_category["sort_order"]

    def test_get_category_not_found(self, client: TestClient) -> None:
        """GET /api/v1/categories/{id} with non-existent ID returns 404."""
        response = client.get("/api/v1/categories/999999")

        assert response.status_code == 404

    def test_get_category_invalid_id_format(self, client: TestClient) -> None:
        """GET /api/v1/categories/{id} with non-integer ID returns 422."""
        response = client.get("/api/v1/categories/not-a-number")

        assert response.status_code == 422

    def test_get_category_negative_id(self, client: TestClient) -> None:
        """GET /api/v1/categories/{id} with negative ID returns 404 or 422."""
        response = client.get("/api/v1/categories/-1")

        assert response.status_code in (404, 422)

    def test_get_category_response_structure(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Response contains all expected fields."""
        category_id = created_category["id"]
        response = client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        data = response.json()
        expected_keys = {
            "id",
            "name",
            "slug",
            "description",
            "parent_id",
            "icon",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
            "product_count",
        }
        assert expected_keys.issubset(data.keys())

    def test_get_category_content_type(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Response Content-Type is application/json."""
        category_id = created_category["id"]
        response = client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_category_does_not_leak_others(
        self, client: TestClient, created_category: dict
    ) -> None:
        """GET /api/v1/categories/{id} only returns the requested category."""
        # Create another category
        other = client.post(
            "/api/v1/categories",
            json={"name": "Other", "slug": "other-category"},
        )
        assert other.status_code == 201

        category_id = created_category["id"]
        response = client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == created_category["name"]

    def test_get_category_after_update_reflects_changes(
        self, client: TestClient, created_category: dict
    ) -> None:
        """GET /api/v1/categories/{id} reflects updates made to the category."""
        category_id = created_category["id"]

        # Update the category
        update_resp = client.put(
            f"/api/v1/categories/{category_id}",
            json={"name": "Updated Name"},
        )
        assert update_resp.status_code == 200

        # Get the category and verify the update
        response = client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"


# ---------------------------------------------------------------------------
# 4. PUT /api/v1/categories/{id}  — test_update_category
# ---------------------------------------------------------------------------


class TestUpdateCategory:
    """Tests for the PUT /api/v1/categories/{id} endpoint."""

    def test_update_category_success(
        self, client: TestClient, created_category: dict
    ) -> None:
        """PUT /api/v1/categories/{id} updates the category and returns it."""
        category_id = created_category["id"]
        update_payload = {"name": "Updated Category Name"}
        response = client.put(
            f"/api/v1/categories/{category_id}", json=update_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == "Updated Category Name"
        # Other fields should remain unchanged
        assert data["slug"] == created_category["slug"]

    def test_update_category_multiple_fields(
        self, client: TestClient, created_category: dict
    ) -> None:
        """PUT /api/v1/categories/{id} can update multiple fields at once."""
        category_id = created_category["id"]
        update_payload = {
            "name": "Multi Update",
            "description": "Updated description",
            "is_active": False,
            "sort_order": 500,
        }
        response = client.put(
            f"/api/v1/categories/{category_id}", json=update_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Multi Update"
        assert data["description"] == "Updated description"
        assert data["is_active"] is False
        assert data["sort_order"] == 500

    def test_update_category_not_found(self, client: TestClient) -> None:
        """PUT /api/v1/categories/{id} with non-existent ID returns 404."""
        response = client.put(
            "/api/v1/categories/999999", json={"name": "NonExistent"}
        )

        assert response.status_code == 404

    def test_update_category_invalid_id_format(self, client: TestClient) -> None:
        """PUT /api/v1/categories/{id} with non-integer ID returns 422."""
        response = client.put(
            "/api/v1/categories/not-a-number", json={"name": "Invalid"}
        )

        assert response.status_code == 422

    def test_update_category_duplicate_slug(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating a category with a duplicate slug returns 409."""
        # Create another category
        other = client.post(
            "/api/v1/categories",
            json={"name": "Other Category", "slug": "other-slug"},
        )
        assert other.status_code == 201

        # Try to update the first category with the second's slug
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"slug": "other-slug"}
        )

        assert response.status_code == 409

    def test_update_category_same_slug_allowed(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating a category keeping its own slug is allowed."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"slug": created_category["slug"]},
        )

        assert response.status_code == 200

    def test_update_category_with_invalid_parent_id(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating a category with a non-existent parent_id returns 400."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"parent_id": 999999}
        )

        assert response.status_code == 400

    def test_update_category_with_valid_parent_id(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating a category with a valid parent_id succeeds."""
        # Create a parent category
        parent = client.post(
            "/api/v1/categories",
            json={"name": "Parent", "slug": "parent-category"},
        )
        assert parent.status_code == 201

        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"parent_id": parent.json()["id"]},
        )

        assert response.status_code == 200
        assert response.json()["parent_id"] == parent.json()["id"]

    def test_update_category_empty_name(self, client: TestClient, created_category: dict) -> None:
        """Updating name to empty string returns 422."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"name": ""}
        )

        assert response.status_code == 422

    def test_update_category_name_too_long(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating name to exceed 100 characters returns 422."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"name": "A" * 101}
        )

        assert response.status_code == 422

    def test_update_category_sort_order_negative(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating sort_order to negative value returns 422."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"sort_order": -1}
        )

        assert response.status_code == 422

    def test_update_category_sort_order_too_large(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating sort_order above 9999 returns 422."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"sort_order": 10000}
        )

        assert response.status_code == 422

    def test_update_category_empty_body(
        self, client: TestClient, created_category: dict
    ) -> None:
        """PUT with empty body returns 200 (all fields are optional in update)."""
        category_id = created_category["id"]
        response = client.put(f"/api/v1/categories/{category_id}", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == created_category["name"]

    def test_update_category_no_body(
        self, client: TestClient, created_category: dict
    ) -> None:
        """PUT with no body returns 422."""
        category_id = created_category["id"]
        response = client.put(f"/api/v1/categories/{category_id}")

        assert response.status_code == 422

    def test_update_category_content_type(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Response Content-Type is application/json."""
        category_id = created_category["id"]
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"name": "Content Type Test"}
        )

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_update_category_updated_at_changes(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating a category changes the updated_at timestamp."""
        category_id = created_category["id"]
        original_updated_at = created_category["updated_at"]

        response = client.put(
            f"/api/v1/categories/{category_id}", json={"name": "Timestamp Test"}
        )

        assert response.status_code == 200
        data = response.json()
        # updated_at should be different from the original
        assert data["updated_at"] != original_updated_at

    def test_update_category_does_not_affect_other_categories(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Updating one category does not modify other categories."""
        # Create another category
        other = client.post(
            "/api/v1/categories",
            json={"name": "Unchanged", "slug": "unchanged-category"},
        )
        assert other.status_code == 201
        other_data = other.json()

        # Update the first category
        category_id = created_category["id"]
        client.put(
            f"/api/v1/categories/{category_id}", json={"name": "Changed"}
        )

        # Verify the other category is unchanged
        response = client.get(f"/api/v1/categories/{other_data['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Unchanged"


# ---------------------------------------------------------------------------
# 5. DELETE /api/v1/categories/{id}  — test_delete_category
# ---------------------------------------------------------------------------


class TestDeleteCategory:
    """Tests for the DELETE /api/v1/categories/{id} endpoint."""

    def test_delete_category_success(
        self, client: TestClient, created_category: dict
    ) -> None:
        """DELETE /api/v1/categories/{id} returns 204 No Content."""
        category_id = created_category["id"]
        response = client.delete(f"/api/v1/categories/{category_id}")

        assert response.status_code == 204

    def test_delete_category_not_found(self, client: TestClient) -> None:
        """DELETE /api/v1/categories/{id} with non-existent ID returns 404."""
        response = client.delete("/api/v1/categories/999999")

        assert response.status_code == 404

    def test_delete_category_invalid_id_format(self, client: TestClient) -> None:
        """DELETE /api/v1/categories/{id} with non-integer ID returns 422."""
        response = client.delete("/api/v1/categories/not-a-number")

        assert response.status_code == 422

    def test_delete_category_removes_from_list(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleted category no longer appears in the list."""
        category_id = created_category["id"]

        # Delete the category
        delete_resp = client.delete(f"/api/v1/categories/{category_id}")
        assert delete_resp.status_code == 204

        # Verify it's gone from the list
        list_resp = client.get("/api/v1/categories", params={"search": created_category["slug"]})
        assert list_resp.status_code == 200
        data = list_resp.json()
        ids = [item["id"] for item in data["items"]]
        assert category_id not in ids

    def test_delete_category_cannot_be_retrieved(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleted category returns 404 when trying to GET it."""
        category_id = created_category["id"]

        # Delete the category
        client.delete(f"/api/v1/categories/{category_id}")

        # Try to get it
        response = client.get(f"/api/v1/categories/{category_id}")
        assert response.status_code == 404

    def test_delete_category_cannot_be_updated(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleted category returns 404 when trying to PUT it."""
        category_id = created_category["id"]

        # Delete the category
        client.delete(f"/api/v1/categories/{category_id}")

        # Try to update it
        response = client.put(
            f"/api/v1/categories/{category_id}", json={"name": "Should Fail"}
        )
        assert response.status_code == 404

    def test_delete_category_cannot_be_deleted_again(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleting an already-deleted category returns 404."""
        category_id = created_category["id"]

        # First delete
        resp1 = client.delete(f"/api/v1/categories/{category_id}")
        assert resp1.status_code == 204

        # Second delete should fail
        resp2 = client.delete(f"/api/v1/categories/{category_id}")
        assert resp2.status_code == 404

    def test_delete_category_no_content_body(
        self, client: TestClient, created_category: dict
    ) -> None:
        """DELETE response has no content body."""
        category_id = created_category["id"]
        response = client.delete(f"/api/v1/categories/{category_id}")

        assert response.status_code == 204
        assert response.content == b""

    def test_delete_category_does_not_affect_others(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleting one category does not affect other categories."""
        # Create another category
        other = client.post(
            "/api/v1/categories",
            json={"name": "Survivor", "slug": "survivor-category"},
        )
        assert other.status_code == 201
        other_id = other.json()["id"]

        # Delete the first category
        category_id = created_category["id"]
        client.delete(f"/api/v1/categories/{category_id}")

        # Verify the other category still exists
        response = client.get(f"/api/v1/categories/{other_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Survivor"

    def test_delete_category_with_children(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Deleting a category that has children succeeds (no cascade restriction)."""
        # Create a child category
        child = client.post(
            "/api/v1/categories",
            json={
                "name": "Child Category",
                "slug": "child-category",
                "parent_id": created_category["id"],
            },
        )
        assert child.status_code == 201

        # Delete the parent
        category_id = created_category["id"]
        response = client.delete(f"/api/v1/categories/{category_id}")

        assert response.status_code == 204

    def test_delete_category_total_count_decreases(
        self, client: TestClient, created_category: dict
    ) -> None:
        """Total category count decreases after deletion."""
        # Get initial count
        initial = client.get("/api/v1/categories", params={"page_size": 100})
        initial_total = initial.json()["total"]

        # Delete a category
        category_id = created_category["id"]
        client.delete(f"/api/v1/categories/{category_id}")

        # Get new count
        after = client.get("/api/v1/categories", params={"page_size": 100})
        after_total = after.json()["total"]

        assert after_total == initial_total - 1
