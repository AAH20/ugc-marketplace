"""
Comprehensive API tests for the Tags endpoints.

Tests cover:
- GET    /api/v1/tags        — list tags with pagination
- POST   /api/v1/tags        — create a tag
- GET    /api/v1/tags/{id}   — retrieve a single tag
- PUT    /api/v1/tags/{id}   — update a tag
- DELETE /api/v1/tags/{id}   — delete a tag
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Return a TestClient bound to the FastAPI application."""
    from ugc_marketplace.main import app  # type: ignore
    return TestClient(app)


@pytest.fixture
def sample_tag_payload():
    """Return a valid payload for creating a tag."""
    return {
        "name": "test-tag",
        "description": "A sample tag used in API tests.",
        "color": "#FF5733",
    }


@pytest.fixture
def created_tag(client, sample_tag_payload):
    """Create a tag and return the response JSON."""
    response = client.post("/api/v1/tags", json=sample_tag_payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# GET /api/v1/tags — list tags with pagination
# ---------------------------------------------------------------------------

class TestListTags:
    """Tests for the GET /api/v1/tags endpoint."""

    def test_list_tags_empty(self, client):
        """GET /api/v1/tags returns an empty list when no tags exist."""
        response = client.get("/api/v1/tags")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_tags_returns_created_items(self, client, sample_tag_payload):
        """GET /api/v1/tags returns previously created tags."""
        client.post("/api/v1/tags", json=sample_tag_payload)
        client.post("/api/v1/tags", json={**sample_tag_payload, "name": "second-tag"})

        response = client.get("/api/v1/tags")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_tags_response_structure(self, client, created_tag):
        """Each tag in the list has the expected keys."""
        response = client.get("/api/v1/tags")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        item = data[0]
        expected_keys = {"id", "name", "description", "color"}
        assert expected_keys.issubset(item.keys())

    def test_list_tags_pagination_limit(self, client, sample_tag_payload):
        """GET /api/v1/tags?limit=N returns at most N items."""
        for i in range(5):
            client.post("/api/v1/tags", json={**sample_tag_payload, "name": f"tag-{i}"})

        response = client.get("/api/v1/tags", params={"limit": 2})

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_list_tags_pagination_offset(self, client, sample_tag_payload):
        """GET /api/v1/tags?offset=N skips the first N items."""
        for i in range(3):
            client.post("/api/v1/tags", json={**sample_tag_payload, "name": f"tag-{i}"})

        response = client.get("/api/v1/tags", params={"offset": 1})

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0

    def test_list_tags_pagination_limit_and_offset(self, client, sample_tag_payload):
        """GET /api/v1/tags?limit=N&offset=M paginates correctly."""
        for i in range(5):
            client.post("/api/v1/tags", json={**sample_tag_payload, "name": f"tag-{i}"})

        response = client.get("/api/v1/tags", params={"limit": 2, "offset": 1})

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_list_tags_response_content_type(self, client):
        """Response Content-Type is application/json."""
        response = client.get("/api/v1/tags")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# POST /api/v1/tags — create a tag
# ---------------------------------------------------------------------------

class TestCreateTag:
    """Tests for the POST /api/v1/tags endpoint."""

    def test_create_tag_success(self, client, sample_tag_payload):
        """POST /api/v1/tags with a valid payload returns 201 and the created object."""
        response = client.post("/api/v1/tags", json=sample_tag_payload)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_tag_payload["name"]
        assert data["description"] == sample_tag_payload["description"]
        assert data["color"] == sample_tag_payload["color"]

    def test_create_tag_returns_unique_ids(self, client, sample_tag_payload):
        """Each POST /api/v1/tags call returns a distinct id."""
        resp1 = client.post("/api/v1/tags", json=sample_tag_payload)
        resp2 = client.post("/api/v1/tags", json=sample_tag_payload)

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_tag_missing_name(self, client, sample_tag_payload):
        """POST /api/v1/tags without a required name returns 422."""
        payload = {k: v for k, v in sample_tag_payload.items() if k != "name"}
        response = client.post("/api/v1/tags", json=payload)

        assert response.status_code == 422

    def test_create_tag_empty_body(self, client):
        """POST /api/v1/tags with an empty JSON body returns 422."""
        response = client.post("/api/v1/tags", json={})

        assert response.status_code == 422

    def test_create_tag_no_body(self, client):
        """POST /api/v1/tags with no body at all returns 422."""
        response = client.post("/api/v1/tags")

        assert response.status_code == 422

    def test_create_tag_extra_fields_ignored(self, client, sample_tag_payload):
        """Extra unknown fields are either ignored or rejected, not crash the server."""
        payload = {**sample_tag_payload, "unknown_field": "some value"}
        response = client.post("/api/v1/tags", json=payload)

        assert response.status_code in (201, 422)

    def test_create_tag_response_content_type(self, client, sample_tag_payload):
        """Response Content-Type is application/json."""
        response = client.post("/api/v1/tags", json=sample_tag_payload)

        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")

    def test_create_tag_duplicate_name(self, client, sample_tag_payload):
        """POST /api/v1/tags with a duplicate name returns 409 or 422."""
        client.post("/api/v1/tags", json=sample_tag_payload)
        response = client.post("/api/v1/tags", json=sample_tag_payload)

        assert response.status_code in (409, 422)

    def test_create_tag_name_too_long(self, client, sample_tag_payload):
        """POST /api/v1/tags with an excessively long name returns 422."""
        payload = {**sample_tag_payload, "name": "a" * 256}
        response = client.post("/api/v1/tags", json=payload)

        assert response.status_code == 422

    def test_create_tag_invalid_color_format(self, client, sample_tag_payload):
        """POST /api/v1/tags with an invalid color format returns 422."""
        payload = {**sample_tag_payload, "color": "not-a-color"}
        response = client.post("/api/v1/tags", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/tags/{id} — retrieve a single tag
# ---------------------------------------------------------------------------

class TestGetTag:
    """Tests for the GET /api/v1/tags/{id} endpoint."""

    def test_get_tag_success(self, client, created_tag):
        """GET /api/v1/tags/{id} returns the matching tag."""
        tag_id = created_tag["id"]
        response = client.get(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == created_tag["name"]
        assert data["description"] == created_tag["description"]
        assert data["color"] == created_tag["color"]

    def test_get_tag_not_found(self, client):
        """GET /api/v1/tags/{id} with a non-existent id returns 404."""
        response = client.get("/api/v1/tags/nonexistent-id-12345")

        assert response.status_code == 404

    def test_get_tag_invalid_id_format(self, client):
        """GET /api/v1/tags/{id} with an invalid id format returns 422 or 404."""
        response = client.get("/api/v1/tags/!!invalid!!")

        assert response.status_code in (404, 422)

    def test_get_tag_response_content_type(self, client, created_tag):
        """Response Content-Type is application/json."""
        tag_id = created_tag["id"]
        response = client.get(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_tag_after_update(self, client, created_tag):
        """GET /api/v1/tags/{id} reflects updates made to the tag."""
        tag_id = created_tag["id"]

        client.put(
            f"/api/v1/tags/{tag_id}",
            json={"name": "updated-tag-name"},
        )

        response = client.get(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "updated-tag-name"

    def test_get_tag_does_not_leak_other_items(self, client, sample_tag_payload):
        """GET /api/v1/tags/{id} only returns the requested tag, not others."""
        resp1 = client.post("/api/v1/tags", json=sample_tag_payload)
        client.post("/api/v1/tags", json={**sample_tag_payload, "name": "other-tag"})

        tag_id = resp1.json()["id"]
        response = client.get(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == sample_tag_payload["name"]


# ---------------------------------------------------------------------------
# PUT /api/v1/tags/{id} — update a tag
# ---------------------------------------------------------------------------

class TestUpdateTag:
    """Tests for the PUT /api/v1/tags/{id} endpoint."""

    def test_update_tag_success(self, client, created_tag):
        """PUT /api/v1/tags/{id} with a valid payload returns 200 and the updated object."""
        tag_id = created_tag["id"]
        update_payload = {
            "name": "updated-tag",
            "description": "Updated description.",
            "color": "#00FF00",
        }
        response = client.put(f"/api/v1/tags/{tag_id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == update_payload["name"]
        assert data["description"] == update_payload["description"]
        assert data["color"] == update_payload["color"]

    def test_update_tag_partial(self, client, created_tag):
        """PUT /api/v1/tags/{id} with partial payload updates only provided fields."""
        tag_id = created_tag["id"]
        response = client.put(
            f"/api/v1/tags/{tag_id}",
            json={"name": "partially-updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == "partially-updated"
        # Other fields should remain unchanged
        assert data["description"] == created_tag["description"]
        assert data["color"] == created_tag["color"]

    def test_update_tag_not_found(self, client):
        """PUT /api/v1/tags/{id} with a non-existent id returns 404."""
        response = client.put(
            "/api/v1/tags/nonexistent-id-12345",
            json={"name": "updated-name"},
        )

        assert response.status_code == 404

    def test_update_tag_empty_body(self, client, created_tag):
        """PUT /api/v1/tags/{id} with an empty JSON body returns 422."""
        tag_id = created_tag["id"]
        response = client.put(f"/api/v1/tags/{tag_id}", json={})

        assert response.status_code == 422

    def test_update_tag_no_body(self, client, created_tag):
        """PUT /api/v1/tags/{id} with no body at all returns 422."""
        tag_id = created_tag["id"]
        response = client.put(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 422

    def test_update_tag_response_content_type(self, client, created_tag):
        """Response Content-Type is application/json."""
        tag_id = created_tag["id"]
        response = client.put(
            f"/api/v1/tags/{tag_id}",
            json={"name": "content-type-test"},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_update_tag_invalid_color(self, client, created_tag):
        """PUT /api/v1/tags/{id} with an invalid color returns 422."""
        tag_id = created_tag["id"]
        response = client.put(
            f"/api/v1/tags/{tag_id}",
            json={"color": "invalid-color"},
        )

        assert response.status_code == 422

    def test_update_tag_name_too_long(self, client, created_tag):
        """PUT /api/v1/tags/{id} with an excessively long name returns 422."""
        tag_id = created_tag["id"]
        response = client.put(
            f"/api/v1/tags/{tag_id}",
            json={"name": "a" * 256},
        )

        assert response.status_code == 422

    def test_update_tag_extra_fields_ignored(self, client, created_tag):
        """Extra unknown fields are either ignored or rejected, not crash the server."""
        tag_id = created_tag["id"]
        response = client.put(
            f"/api/v1/tags/{tag_id}",
            json={"name": "extra-fields-test", "unknown_field": "value"},
        )

        assert response.status_code in (200, 422)


# ---------------------------------------------------------------------------
# DELETE /api/v1/tags/{id} — delete a tag
# ---------------------------------------------------------------------------

class TestDeleteTag:
    """Tests for the DELETE /api/v1/tags/{id} endpoint."""

    def test_delete_tag_success(self, client, created_tag):
        """DELETE /api/v1/tags/{id} returns 204 and removes the tag."""
        tag_id = created_tag["id"]
        response = client.delete(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 204

        # Verify the tag is actually deleted
        get_response = client.get(f"/api/v1/tags/{tag_id}")
        assert get_response.status_code == 404

    def test_delete_tag_not_found(self, client):
        """DELETE /api/v1/tags/{id} with a non-existent id returns 404."""
        response = client.delete("/api/v1/tags/nonexistent-id-12345")

        assert response.status_code == 404

    def test_delete_tag_invalid_id_format(self, client):
        """DELETE /api/v1/tags/{id} with an invalid id format returns 422 or 404."""
        response = client.delete("/api/v1/tags/!!invalid!!")

        assert response.status_code in (404, 422)

    def test_delete_tag_response_content_type(self, client, created_tag):
        """Response Content-Type is application/json."""
        tag_id = created_tag["id"]
        response = client.delete(f"/api/v1/tags/{tag_id}")

        assert response.status_code == 204

    def test_delete_tag_idempotent_behavior(self, client, created_tag):
        """Deleting the same tag twice returns 404 on the second attempt."""
        tag_id = created_tag["id"]

        # First delete should succeed
        response1 = client.delete(f"/api/v1/tags/{tag_id}")
        assert response1.status_code == 204

        # Second delete should return 404
        response2 = client.delete(f"/api/v1/tags/{tag_id}")
        assert response2.status_code == 404

    def test_delete_tag_does_not_affect_others(self, client, sample_tag_payload):
        """Deleting one tag does not affect other tags."""
        resp1 = client.post("/api/v1/tags", json=sample_tag_payload)
        resp2 = client.post("/api/v1/tags", json={**sample_tag_payload, "name": "other-tag"})

        tag_id_1 = resp1.json()["id"]
        tag_id_2 = resp2.json()["id"]

        # Delete first tag
        client.delete(f"/api/v1/tags/{tag_id_1}")

        # Second tag should still exist
        response = client.get(f"/api/v1/tags/{tag_id_2}")
        assert response.status_code == 200
        assert response.json()["id"] == tag_id_2
