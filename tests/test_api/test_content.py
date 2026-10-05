"""
Comprehensive API tests for the Content endpoints.

Tests cover:
- GET    /api/v1/content          — list content with pagination and filters
- POST   /api/v1/content          — create content
- GET    /api/v1/content/{id}     — retrieve a single content item
- PUT    /api/v1/content/{id}     — update content
- DELETE /api/v1/content/{id}     — delete content
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to the FastAPI application."""
    from ugc_marketplace.main import app

    return TestClient(app)


@pytest.fixture
def sample_content_payload() -> dict:
    """Return a valid payload for creating content."""
    return {
        "title": "Test Content Item",
        "type": "image",
        "author_id": "user-001",
        "description": "A sample content item used in API tests.",
        "tags": ["test", "api", "pytest"],
        "media_url": "https://cdn.example.com/media/test.jpg",
    }


@pytest.fixture
def created_content(client: TestClient, sample_content_payload: dict) -> dict:
    """Create a content item and return the response JSON."""
    response = client.post("/api/v1/content", json=sample_content_payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# GET /api/v1/content  — test_list_content
# ---------------------------------------------------------------------------


class TestListContent:
    """Tests for GET /api/v1/content."""

    def test_list_content_success(self, client: TestClient) -> None:
        """GET /api/v1/content returns 200 with paginated structure."""
        response = client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_content_pagination_first_page(self, client: TestClient) -> None:
        """GET /api/v1/content returns the first page by default."""
        response = client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] >= 0
        assert data["total_pages"] >= 1

    def test_list_content_pagination_custom_page(self, client: TestClient) -> None:
        """GET /api/v1/content?page=2 returns the second page."""
        response = client.get("/api/v1/content", params={"page": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2

    def test_list_content_pagination_custom_page_size(self, client: TestClient) -> None:
        """GET /api/v1/content?page_size=5 limits items per page."""
        response = client.get("/api/v1/content", params={"page_size": 5})

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

    def test_list_content_pagination_page_size_one(self, client: TestClient) -> None:
        """GET /api/v1/content?page_size=1 returns exactly one item per page."""
        response = client.get("/api/v1/content", params={"page_size": 1})

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 1
        assert len(data["items"]) <= 1

    def test_list_content_pagination_total_pages(self, client: TestClient) -> None:
        """total_pages is calculated correctly based on total and page_size."""
        response = client.get("/api/v1/content", params={"page_size": 3})

        assert response.status_code == 200
        data = response.json()
        expected_pages = (data["total"] + 2) // 3
        assert data["total_pages"] == expected_pages

    def test_list_content_filter_by_type(self, client: TestClient) -> None:
        """GET /api/v1/content?type=image filters by content type."""
        response = client.get("/api/v1/content", params={"type": "image"})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "image"

    def test_list_content_filter_by_status(self, client: TestClient) -> None:
        """GET /api/v1/content?status=published filters by status."""
        response = client.get("/api/v1/content", params={"status": "published"})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "published"

    def test_list_content_filter_by_type_and_status(self, client: TestClient) -> None:
        """GET /api/v1/content?type=video&status=published filters by both."""
        response = client.get(
            "/api/v1/content",
            params={"type": "video", "status": "published"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "video"
            assert item["status"] == "published"

    def test_list_content_invalid_type_filter(self, client: TestClient) -> None:
        """GET /api/v1/content?type=invalid returns 422."""
        response = client.get("/api/v1/content", params={"type": "invalid"})

        assert response.status_code == 422

    def test_list_content_invalid_status_filter(self, client: TestClient) -> None:
        """GET /api/v1/content?status=invalid returns 422."""
        response = client.get("/api/v1/content", params={"status": "invalid"})

        assert response.status_code == 422

    def test_list_content_page_zero(self, client: TestClient) -> None:
        """GET /api/v1/content?page=0 returns 422 (page must be >= 1)."""
        response = client.get("/api/v1/content", params={"page": 0})

        assert response.status_code == 422

    def test_list_content_page_size_zero(self, client: TestClient) -> None:
        """GET /api/v1/content?page_size=0 returns 422."""
        response = client.get("/api/v1/content", params={"page_size": 0})

        assert response.status_code == 422

    def test_list_content_page_size_too_large(self, client: TestClient) -> None:
        """GET /api/v1/content?page_size=101 returns 422 (max 100)."""
        response = client.get("/api/v1/content", params={"page_size": 101})

        assert response.status_code == 422

    def test_list_content_response_content_type(self, client: TestClient) -> None:
        """Response Content-Type is application/json."""
        response = client.get("/api/v1/content")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_list_content_items_have_required_fields(self, client: TestClient) -> None:
        """Each item in the list has the expected keys."""
        response = client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            expected_keys = {
                "id",
                "title",
                "type",
                "status",
                "author_id",
                "tags",
                "media_url",
                "description",
                "created_at",
                "updated_at",
                "views",
                "likes",
            }
            assert expected_keys.issubset(item.keys())


# ---------------------------------------------------------------------------
# POST /api/v1/content  — test_create_content
# ---------------------------------------------------------------------------


class TestCreateContent:
    """Tests for POST /api/v1/content."""

    def test_create_content_success(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content with valid payload returns 201 and the created object."""
        response = client.post("/api/v1/content", json=sample_content_payload)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == sample_content_payload["title"]
        assert data["type"] == sample_content_payload["type"]
        assert data["author_id"] == sample_content_payload["author_id"]
        assert data["description"] == sample_content_payload["description"]
        assert data["tags"] == sample_content_payload["tags"]
        assert data["media_url"] == sample_content_payload["media_url"]
        assert data["status"] == "draft"
        assert data["views"] == 0
        assert data["likes"] == 0
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_content_minimal_fields(self, client: TestClient) -> None:
        """POST /api/v1/content with only required fields succeeds."""
        payload = {"title": "Minimal", "type": "video", "author_id": "user-002"}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal"
        assert data["type"] == "video"
        assert data["author_id"] == "user-002"
        assert data["tags"] == []
        assert data["description"] is None
        assert data["media_url"] is None

    def test_create_content_returns_unique_ids(self, client: TestClient, sample_content_payload: dict) -> None:
        """Each POST /api/v1/content call returns a distinct id."""
        resp1 = client.post("/api/v1/content", json=sample_content_payload)
        resp2 = client.post("/api/v1/content", json=sample_content_payload)

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_content_missing_title(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content without title returns 422."""
        payload = {k: v for k, v in sample_content_payload.items() if k != "title"}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_missing_type(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content without type returns 422."""
        payload = {k: v for k, v in sample_content_payload.items() if k != "type"}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_missing_author_id(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content without author_id returns 422."""
        payload = {k: v for k, v in sample_content_payload.items() if k != "author_id"}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_invalid_type(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content with unsupported type returns 422."""
        payload = {**sample_content_payload, "type": "unsupported_type"}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_empty_title(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content with empty title returns 422."""
        payload = {**sample_content_payload, "title": ""}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_title_too_long(self, client: TestClient, sample_content_payload: dict) -> None:
        """POST /api/v1/content with title > 200 chars returns 422."""
        payload = {**sample_content_payload, "title": "x" * 201}
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422

    def test_create_content_empty_body(self, client: TestClient) -> None:
        """POST /api/v1/content with empty JSON body returns 422."""
        response = client.post("/api/v1/content", json={})

        assert response.status_code == 422

    def test_create_content_no_body(self, client: TestClient) -> None:
        """POST /api/v1/content with no body returns 422."""
        response = client.post("/api/v1/content")

        assert response.status_code == 422

    def test_create_content_response_content_type(self, client: TestClient, sample_content_payload: dict) -> None:
        """Response Content-Type is application/json."""
        response = client.post("/api/v1/content", json=sample_content_payload)

        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")

    def test_create_content_all_valid_types(self, client: TestClient) -> None:
        """POST /api/v1/content accepts all valid content types."""
        for content_type in ("image", "video", "review"):
            payload = {
                "title": f"Test {content_type}",
                "type": content_type,
                "author_id": "user-001",
            }
            response = client.post("/api/v1/content", json=payload)
            assert response.status_code == 201
            assert response.json()["type"] == content_type

    def test_create_content_with_many_tags(self, client: TestClient) -> None:
        """POST /api/v1.content with up to 20 tags succeeds."""
        payload = {
            "title": "Many Tags",
            "type": "image",
            "author_id": "user-001",
            "tags": [f"tag-{i}" for i in range(20)],
        }
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 201
        assert len(response.json()["tags"]) == 20

    def test_create_content_too_many_tags(self, client: TestClient) -> None:
        """POST /api/v1/content with > 20 tags returns 422."""
        payload = {
            "title": "Too Many Tags",
            "type": "image",
            "author_id": "user-001",
            "tags": [f"tag-{i}" for i in range(21)],
        }
        response = client.post("/api/v1/content", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/content/{id}  — test_get_content
# ---------------------------------------------------------------------------


class TestGetContent:
    """Tests for GET /api/v1/content/{id}."""

    def test_get_content_success(self, client: TestClient, created_content: dict) -> None:
        """GET /api/v1/content/{id} returns the matching content item."""
        content_id = created_content["id"]
        response = client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content_id
        assert data["title"] == created_content["title"]
        assert data["type"] == created_content["type"]
        assert data["author_id"] == created_content["author_id"]
        assert data["description"] == created_content["description"]
        assert data["tags"] == created_content["tags"]
        assert data["media_url"] == created_content["media_url"]
        assert data["status"] == created_content["status"]

    def test_get_content_not_found(self, client: TestClient) -> None:
        """GET /api/v1/content/{id} with non-existent id returns 404."""
        response = client.get("/api/v1/content/nonexistent-id-12345")

        assert response.status_code == 404

    def test_get_content_response_content_type(self, client: TestClient, created_content: dict) -> None:
        """Response Content-Type is application/json."""
        content_id = created_content["id"]
        response = client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_content_has_all_fields(self, client: TestClient, created_content: dict) -> None:
        """GET /api/v1/content/{id} returns all expected fields."""
        content_id = created_content["id"]
        response = client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        expected_keys = {
            "id",
            "title",
            "type",
            "status",
            "author_id",
            "tags",
            "media_url",
            "description",
            "created_at",
            "updated_at",
            "views",
            "likes",
        }
        assert expected_keys.issubset(data.keys())

    def test_get_content_does_not_leak_other_items(self, client: TestClient, sample_content_payload: dict) -> None:
        """GET /api/v1/content/{id} only returns the requested item."""
        resp1 = client.post("/api/v1/content", json=sample_content_payload)
        client.post("/api/v1/content", json={**sample_content_payload, "title": "Other Item"})

        content_id = resp1.json()["id"]
        response = client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content_id
        assert data["title"] == sample_content_payload["title"]

    def test_get_content_after_update(self, client: TestClient, created_content: dict) -> None:
        """GET /api/v1/content/{id} reflects updates made to the content."""
        content_id = created_content["id"]

        client.put(
            f"/api/v1/content/{content_id}",
            json={"title": "Updated Title"},
        )

        response = client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# PUT /api/v1/content/{id}  — test_update_content
# ---------------------------------------------------------------------------


class TestUpdateContent:
    """Tests for PUT /api/v1/content/{id}."""

    def test_update_content_success(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} with valid payload returns 200 and updated object."""
        content_id = created_content["id"]
        update_payload = {"title": "Updated Title"}
        response = client.put(f"/api/v1/content/{content_id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content_id
        assert data["title"] == "Updated Title"
        # Other fields should remain unchanged
        assert data["type"] == created_content["type"]
        assert data["author_id"] == created_content["author_id"]

    def test_update_content_status(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} can update status."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"status": "published"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_update_content_description(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} can update description."""
        content_id = created_content["id"]
        new_desc = "Updated description for testing."
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"description": new_desc},
        )

        assert response.status_code == 200
        assert response.json()["description"] == new_desc

    def test_update_content_tags(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} can update tags."""
        content_id = created_content["id"]
        new_tags = ["updated", "tags"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"tags": new_tags},
        )

        assert response.status_code == 200
        assert response.json()["tags"] == new_tags

    def test_update_content_media_url(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} can update media_url."""
        content_id = created_content["id"]
        new_url = "https://cdn.example.com/media/updated.jpg"
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"media_url": new_url},
        )

        assert response.status_code == 200
        assert response.json()["media_url"] == new_url

    def test_update_content_multiple_fields(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} can update multiple fields at once."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={
                "title": "New Title",
                "description": "New Description",
                "tags": ["new", "tags"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["description"] == "New Description"
        assert data["tags"] == ["new", "tags"]

    def test_update_content_not_found(self, client: TestClient) -> None:
        """PUT /api/v1/content/{id} with non-existent id returns 404."""
        response = client.put(
            "/api/v1/content/nonexistent-id-12345",
            json={"title": "Updated"},
        )

        assert response.status_code == 404

    def test_update_content_invalid_status(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} with invalid status returns 422."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"status": "invalid_status"},
        )

        assert response.status_code == 422

    def test_update_content_invalid_type(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} with invalid type returns 422."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"type": "invalid_type"},
        )

        assert response.status_code == 422

    def test_update_content_empty_title(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} with empty title returns 422."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"title": ""},
        )

        assert response.status_code == 422

    def test_update_content_response_content_type(self, client: TestClient, created_content: dict) -> None:
        """Response Content-Type is application/json."""
        content_id = created_content["id"]
        response = client.put(
            f"/api/v1/content/{content_id}",
            json={"title": "Updated"},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_update_content_all_valid_statuses(self, client: TestClient, created_content: dict) -> None:
        """PUT /api/v1/content/{id} accepts all valid status values."""
        content_id = created_content["id"]
        for status_val in ("draft", "pending", "published", "archived"):
            response = client.put(
                f"/api/v1/content/{content_id}",
                json={"status": status_val},
            )
            assert response.status_code == 200
            assert response.json()["status"] == status_val


# ---------------------------------------------------------------------------
# DELETE /api/v1/content/{id}  — test_delete_content
# ---------------------------------------------------------------------------


class TestDeleteContent:
    """Tests for DELETE /api/v1/content/{id}."""

    def test_delete_content_success(self, client: TestClient, created_content: dict) -> None:
        """DELETE /api/v1/content/{id} returns 204 No Content."""
        content_id = created_content["id"]
        response = client.delete(f"/api/v1/content/{content_id}")

        assert response.status_code == 204

    def test_delete_content_removes_item(self, client: TestClient, created_content: dict) -> None:
        """After deletion, GET /api/v1/content/{id} returns 404."""
        content_id = created_content["id"]

        client.delete(f"/api/v1/content/{content_id}")

        response = client.get(f"/api/v1/content/{content_id}")
        assert response.status_code == 404

    def test_delete_content_not_found(self, client: TestClient) -> None:
        """DELETE /api/v1/content/{id} with non-existent id returns 404."""
        response = client.delete("/api/v1/content/nonexistent-id-12345")

        assert response.status_code == 404

    def test_delete_content_empty_body(self, client: TestClient, created_content: dict) -> None:
        """DELETE /api/v1/content/{id} returns no response body."""
        content_id = created_content["id"]
        response = client.delete(f"/api/v1/content/{content_id}")

        assert response.status_code == 204
        assert response.content == b""

    def test_delete_content_then_list_excludes_it(self, client: TestClient, created_content: dict) -> None:
        """Deleted content no longer appears in the list."""
        content_id = created_content["id"]

        client.delete(f"/api/v1/content/{content_id}")

        response = client.get("/api/v1/content", params={"page_size": 100})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["id"] != content_id

    def test_delete_content_id_reuse_not_allowed(self, client: TestClient, created_content: dict) -> None:
        """Deleting the same id twice returns 404 on the second attempt."""
        content_id = created_content["id"]

        response1 = client.delete(f"/api/v1/content/{content_id}")
        assert response1.status_code == 204

        response2 = client.delete(f"/api/v1/content/{content_id}")
        assert response2.status_code == 404
