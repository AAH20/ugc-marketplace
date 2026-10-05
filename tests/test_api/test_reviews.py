"""Comprehensive API tests for the Reviews endpoints."""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app):
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_review_payload():
    """Return a valid payload for creating a review."""
    return {
        "product_id": "prod-001",
        "user_id": "user-001",
        "rating": 5,
        "title": "Excellent product",
        "body": "This product exceeded my expectations. Highly recommended!",
    }


@pytest.fixture
def created_review(client, sample_review_payload):
    """Create a review and return the response JSON."""
    response = client.post("/api/v1/reviews", json=sample_review_payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def multiple_reviews(client):
    """Create multiple reviews for pagination tests."""
    reviews = []
    for i in range(5):
        payload = {
            "product_id": f"prod-{i:03d}",
            "user_id": f"user-{i:03d}",
            "rating": (i % 5) + 1,
            "title": f"Review {i}",
            "body": f"Body of review {i}",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 201
        reviews.append(response.json())
    return reviews


# ---------------------------------------------------------------------------
# 1. test_list_reviews — GET /api/v1/reviews with pagination
# ---------------------------------------------------------------------------


class TestListReviews:
    """Tests for GET /api/v1/reviews."""

    def test_list_reviews_returns_200(self, client):
        """GET /api/v1/reviews should return 200 OK."""
        response = client.get("/api/v1/reviews")
        assert response.status_code == 200

    def test_list_reviews_returns_list(self, client):
        """GET /api/v1/reviews should return a JSON list."""
        response = client.get("/api/v1/reviews")
        data = response.json()
        assert isinstance(data, list)

    def test_list_reviews_empty(self, client):
        """GET /api/v1/reviews with no reviews should return an empty list."""
        response = client.get("/api/v1/reviews")
        data = response.json()
        assert data == []

    def test_list_reviews_returns_created_reviews(self, client, multiple_reviews):
        """GET /api/v1/reviews should return all created reviews."""
        response = client.get("/api/v1/reviews")
        data = response.json()
        assert len(data) == len(multiple_reviews)

    def test_list_reviews_pagination_limit(self, client, multiple_reviews):
        """GET /api/v1/reviews?limit=N should return at most N reviews."""
        limit = 3
        response = client.get(f"/api/v1/reviews?limit={limit}")
        data = response.json()
        assert len(data) <= limit

    def test_list_reviews_pagination_offset(self, client, multiple_reviews):
        """GET /api/v1/reviews?offset=N should skip the first N reviews."""
        offset = 2
        response = client.get(f"/api/v1/reviews?offset={offset}")
        data = response.json()
        all_response = client.get("/api/v1/reviews")
        all_data = all_response.json()
        assert len(data) == len(all_data) - offset

    def test_list_reviews_pagination_limit_and_offset(self, client, multiple_reviews):
        """GET /api/v1/reviews?limit=N&offset=M should paginate correctly."""
        limit = 2
        offset = 1
        response = client.get(f"/api/v1/reviews?limit={limit}&offset={offset}")
        data = response.json()
        assert len(data) <= limit

    def test_list_reviews_response_fields(self, client, created_review):
        """Each review in the list should have expected fields."""
        response = client.get("/api/v1/reviews")
        data = response.json()
        assert len(data) > 0
        review = data[0]
        assert "id" in review
        assert "product_id" in review
        assert "user_id" in review
        assert "rating" in review
        assert "title" in review
        assert "body" in review

    def test_list_reviews_pagination_zero_limit(self, client, multiple_reviews):
        """GET /api/v1/reviews?limit=0 should return empty list."""
        response = client.get("/api/v1/reviews?limit=0")
        data = response.json()
        assert data == []

    def test_list_reviews_pagination_large_offset(self, client, multiple_reviews):
        """GET /api/v1/reviews?offset=9999 should return empty list."""
        response = client.get("/api/v1/reviews?offset=9999")
        data = response.json()
        assert data == []


# ---------------------------------------------------------------------------
# 2. test_create_review — POST /api/v1/reviews
# ---------------------------------------------------------------------------


class TestCreateReview:
    """Tests for POST /api/v1/reviews."""

    def test_create_review_returns_201(self, client, sample_review_payload):
        """POST /api/v1/reviews should return 201 Created."""
        response = client.post("/api/v1/reviews", json=sample_review_payload)
        assert response.status_code == 201

    def test_create_review_returns_review_object(self, client, sample_review_payload):
        """POST /api/v1/reviews should return the created review."""
        response = client.post("/api/v1/reviews", json=sample_review_payload)
        data = response.json()
        assert "id" in data
        assert data["product_id"] == sample_review_payload["product_id"]
        assert data["user_id"] == sample_review_payload["user_id"]
        assert data["rating"] == sample_review_payload["rating"]
        assert data["title"] == sample_review_payload["title"]
        assert data["body"] == sample_review_payload["body"]

    def test_create_review_generates_id(self, client, sample_review_payload):
        """POST /api/v1/reviews should generate a unique id."""
        response1 = client.post("/api/v1/reviews", json=sample_review_payload)
        response2 = client.post("/api/v1/reviews", json=sample_review_payload)
        data1 = response1.json()
        data2 = response2.json()
        assert data1["id"] != data2["id"]

    def test_create_review_missing_product_id(self, client):
        """POST /api/v1/reviews without product_id should return 422."""
        payload = {
            "user_id": "user-001",
            "rating": 5,
            "title": "Title",
            "body": "Body",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 422

    def test_create_review_missing_user_id(self, client):
        """POST /api/v1/reviews without user_id should return 422."""
        payload = {
            "product_id": "prod-001",
            "rating": 5,
            "title": "Title",
            "body": "Body",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 422

    def test_create_review_missing_rating(self, client):
        """POST /api/v1/reviews without rating should return 422."""
        payload = {
            "product_id": "prod-001",
            "user_id": "user-001",
            "title": "Title",
            "body": "Body",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 422

    def test_create_review_invalid_rating_too_high(self, client):
        """POST /api/v1/reviews with rating > 5 should return 422."""
        payload = {
            "product_id": "prod-001",
            "user_id": "user-001",
            "rating": 6,
            "title": "Title",
            "body": "Body",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 422

    def test_create_review_invalid_rating_too_low(self, client):
        """POST /api/v1/reviews with rating < 1 should return 422."""
        payload = {
            "product_id": "prod-001",
            "user_id": "user-001",
            "rating": 0,
            "title": "Title",
            "body": "Body",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 422

    def test_create_review_empty_body(self, client):
        """POST /api/v1/reviews with empty body should return 422."""
        response = client.post("/api/v1/reviews", json={})
        assert response.status_code == 422

    def test_create_review_rating_boundary_1(self, client):
        """POST /api/v1/reviews with rating=1 should succeed."""
        payload = {
            "product_id": "prod-001",
            "user_id": "user-001",
            "rating": 1,
            "title": "Terrible",
            "body": "Worst product ever",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 201

    def test_create_review_rating_boundary_5(self, client):
        """POST /api/v1/reviews with rating=5 should succeed."""
        payload = {
            "product_id": "prod-001",
            "user_id": "user-001",
            "rating": 5,
            "title": "Perfect",
            "body": "Best product ever",
        }
        response = client.post("/api/v1/reviews", json=payload)
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# 3. test_get_review — GET /api/v1/reviews/{id}
# ---------------------------------------------------------------------------


class TestGetReview:
    """Tests for GET /api/v1/reviews/{id}."""

    def test_get_review_returns_200(self, client, created_review):
        """GET /api/v1/reviews/{id} should return 200 for existing review."""
        review_id = created_review["id"]
        response = client.get(f"/api/v1/reviews/{review_id}")
        assert response.status_code == 200

    def test_get_review_returns_correct_review(self, client, created_review):
        """GET /api/v1/reviews/{id} should return the correct review."""
        review_id = created_review["id"]
        response = client.get(f"/api/v1/reviews/{review_id}")
        data = response.json()
        assert data["id"] == review_id
        assert data["product_id"] == created_review["product_id"]
        assert data["user_id"] == created_review["user_id"]
        assert data["rating"] == created_review["rating"]
        assert data["title"] == created_review["title"]
        assert data["body"] == created_review["body"]

    def test_get_review_not_found(self, client):
        """GET /api/v1/reviews/{id} with non-existent id should return 404."""
        response = client.get("/api/v1/reviews/non-existent-id")
        assert response.status_code == 404

    def test_get_review_invalid_id_format(self, client):
        """GET /api/v1/reviews/{id} with invalid id format should return 404."""
        response = client.get("/api/v1/reviews/!!!invalid!!!")
        assert response.status_code == 404

    def test_get_review_response_fields(self, client, created_review):
        """GET /api/v1/reviews/{id} should return all expected fields."""
        review_id = created_review["id"]
        response = client.get(f"/api/v1/reviews/{review_id}")
        data = response.json()
        assert "id" in data
        assert "product_id" in data
        assert "user_id" in data
        assert "rating" in data
        assert "title" in data
        assert "body" in data


# ---------------------------------------------------------------------------
# 4. test_update_review — PUT /api/v1/reviews/{id}
# ---------------------------------------------------------------------------


class TestUpdateReview:
    """Tests for PUT /api/v1/reviews/{id}."""

    def test_update_review_returns_200(self, client, created_review):
        """PUT /api/v1/reviews/{id} should return 200 for existing review."""
        review_id = created_review["id"]
        update_payload = {"rating": 3, "title": "Updated title"}
        response = client.put(f"/api/v1/reviews/{review_id}", json=update_payload)
        assert response.status_code == 200

    def test_update_review_updates_fields(self, client, created_review):
        """PUT /api/v1/reviews/{id} should update the specified fields."""
        review_id = created_review["id"]
        update_payload = {"rating": 3, "title": "Updated title", "body": "Updated body"}
        response = client.put(f"/api/v1/reviews/{review_id}", json=update_payload)
        data = response.json()
        assert data["rating"] == 3
        assert data["title"] == "Updated title"
        assert data["body"] == "Updated body"

    def test_update_review_preserves_unspecified_fields(self, client, created_review):
        """PUT /api/v1/reviews/{id} should preserve fields not in the payload."""
        review_id = created_review["id"]
        update_payload = {"rating": 4}
        response = client.put(f"/api/v1/reviews/{review_id}", json=update_payload)
        data = response.json()
        assert data["rating"] == 4
        assert data["title"] == created_review["title"]
        assert data["body"] == created_review["body"]
        assert data["product_id"] == created_review["product_id"]
        assert data["user_id"] == created_review["user_id"]

    def test_update_review_not_found(self, client):
        """PUT /api/v1/reviews/{id} with non-existent id should return 404."""
        update_payload = {"rating": 3}
        response = client.put("/api/v1/reviews/non-existent-id", json=update_payload)
        assert response.status_code == 404

    def test_update_review_invalid_rating(self, client, created_review):
        """PUT /api/v1/reviews/{id} with invalid rating should return 422."""
        review_id = created_review["id"]
        update_payload = {"rating": 10}
        response = client.put(f"/api/v1/reviews/{review_id}", json=update_payload)
        assert response.status_code == 422

    def test_update_review_empty_payload(self, client, created_review):
        """PUT /api/v1/reviews/{id} with empty payload should return 200 or 422."""
        review_id = created_review["id"]
        response = client.put(f"/api/v1/reviews/{review_id}", json={})
        # Either no-op success or validation error is acceptable
        assert response.status_code in (200, 422)

    def test_update_review_returns_updated_review(self, client, created_review):
        """PUT /api/v1/reviews/{id} should return the updated review object."""
        review_id = created_review["id"]
        update_payload = {"rating": 2, "title": "New title"}
        response = client.put(f"/api/v1/reviews/{review_id}", json=update_payload)
        data = response.json()
        assert data["id"] == review_id
        assert data["rating"] == 2
        assert data["title"] == "New title"


# ---------------------------------------------------------------------------
# 5. test_delete_review — DELETE /api/v1/reviews/{id}
# ---------------------------------------------------------------------------


class TestDeleteReview:
    """Tests for DELETE /api/v1/reviews/{id}."""

    def test_delete_review_returns_204(self, client, created_review):
        """DELETE /api/v1/reviews/{id} should return 204 No Content."""
        review_id = created_review["id"]
        response = client.delete(f"/api/v1/reviews/{review_id}")
        assert response.status_code == 204

    def test_delete_review_removes_review(self, client, created_review):
        """DELETE /api/v1/reviews/{id} should remove the review."""
        review_id = created_review["id"]
        client.delete(f"/api/v1/reviews/{review_id}")
        # Verify it's gone
        response = client.get(f"/api/v1/reviews/{review_id}")
        assert response.status_code == 404

    def test_delete_review_not_found(self, client):
        """DELETE /api/v1/reviews/{id} with non-existent id should return 404."""
        response = client.delete("/api/v1/reviews/non-existent-id")
        assert response.status_code == 404

    def test_delete_review_idempotent_behavior(self, client, created_review):
        """Deleting a review twice should return 404 on the second attempt."""
        review_id = created_review["id"]
        response1 = client.delete(f"/api/v1/reviews/{review_id}")
        assert response1.status_code == 204
        response2 = client.delete(f"/api/v1/reviews/{review_id}")
        assert response2.status_code == 404

    def test_delete_review_does_not_affect_others(self, client, multiple_reviews):
        """Deleting one review should not affect other reviews."""
        review_to_delete = multiple_reviews[0]
        review_to_keep = multiple_reviews[1]
        client.delete(f"/api/v1/reviews/{review_to_delete['id']}")
        # Verify the other review still exists
        response = client.get(f"/api/v1/reviews/{review_to_keep['id']}")
        assert response.status_code == 200

    def test_delete_review_returns_no_content(self, client, created_review):
        """DELETE /api/v1/reviews/{id} should return empty body."""
        review_id = created_review["id"]
        response = client.delete(f"/api/v1/reviews/{review_id}")
        assert response.content == b""
