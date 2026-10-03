"""
Comprehensive API tests for the Listings endpoints.

Tests cover:
    - GET    /api/v1/listings        (list with pagination)
    - POST   /api/v1/listings        (create)
    - GET    /api/v1/listings/{id}   (get by ID)
    - PUT    /api/v1/listings/{id}   (update)
    - DELETE /api/v1/listings/{id}   (delete)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_listing_payload(**overrides: object) -> dict:
    """Return a valid listing payload, with optional field overrides."""
    payload: dict = {
        "seller_id": "usr_test_001",
        "title": "Test Listing Item",
        "description": "A comprehensive test listing description with enough detail",
        "price": 29.99,
        "currency": "USD",
        "category": "video",
        "tags": ["test", "sample"],
    }
    payload.update(overrides)
    return payload


def _create_listing(client: TestClient, **overrides: object) -> dict:
    """Create a listing and return the response JSON."""
    payload = _sample_listing_payload(**overrides)
    response = client.post("/api/v1/listings", json=payload)
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# 1. GET /api/v1/listings  — test_list_listings
# ---------------------------------------------------------------------------

class TestListListings:
    """Tests for GET /api/v1/listings with pagination."""

    def test_list_listings_success(self, client: TestClient) -> None:
        """GET /api/v1/listings returns 200 with paginated structure."""
        response = client.get("/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["data"], list)

    def test_list_listings_default_pagination(self, client: TestClient) -> None:
        """Default pagination returns page 1 with default page_size."""
        response = client.get("/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_listings_custom_page_size(self, client: TestClient) -> None:
        """Custom page_size parameter is respected."""
        response = client.get("/api/v1/listings", params={"page_size": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 5
        assert len(data["data"]) <= 5

    def test_list_listings_custom_page(self, client: TestClient) -> None:
        """Custom page parameter returns the correct page."""
        response = client.get("/api/v1/listings", params={"page": 2, "page_size": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2

    def test_list_listings_pagination_consistency(self, client: TestClient) -> None:
        """Pagination metadata is consistent with data."""
        response = client.get("/api/v1/listings", params={"page": 1, "page_size": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= data["page_size"]
        assert data["total"] >= len(data["data"])
        expected_pages = max(1, (data["total"] + data["page_size"] - 1) // data["page_size"])
        assert data["total_pages"] == expected_pages

    def test_list_listings_empty_page(self, client: TestClient) -> None:
        """Requesting a page beyond available data returns empty list."""
        response = client.get("/api/v1/listings", params={"page": 9999, "page_size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    def test_list_listings_filter_by_category(self, client: TestClient) -> None:
        """Filtering by category returns only matching listings."""
        _create_listing(client, title="Video Listing One", category="video")
        _create_listing(client, title="Photo Listing One", category="photography")

        response = client.get("/api/v1/listings", params={"category": "video"})
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["category"] == "video"

    def test_list_listings_filter_by_price_range(self, client: TestClient) -> None:
        """Filtering by min_price and max_price returns only matching listings."""
        _create_listing(client, title="Cheap Item", price=10.0)
        _create_listing(client, title="Expensive Item", price=500.0)

        response = client.get("/api/v1/listings", params={"min_price": 100.0, "max_price": 1000.0})
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert 100.0 <= item["price"] <= 1000.0

    def test_list_listings_search_query(self, client: TestClient) -> None:
        """Search parameter filters listings by title/description."""
        _create_listing(client, title="UniqueSearchKeyword Item")
        response = client.get("/api/v1/listings", params={"search": "UniqueSearchKeyword"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0

    def test_list_listings_sort_by_price_asc(self, client: TestClient) -> None:
        """Sorting by price ascending returns correctly ordered results."""
        _create_listing(client, title="Sort Test A", price=100.0)
        _create_listing(client, title="Sort Test B", price=10.0)
        response = client.get("/api/v1/listings", params={"sort_by": "price", "sort_order": "asc"})
        assert response.status_code == 200
        data = response.json()
        prices = [item["price"] for item in data["data"]]
        assert prices == sorted(prices)

    def test_list_listings_sort_by_price_desc(self, client: TestClient) -> None:
        """Sorting by price descending returns correctly ordered results."""
        _create_listing(client, title="Sort Test C", price=100.0)
        _create_listing(client, title="Sort Test D", price=10.0)
        response = client.get("/api/v1/listings", params={"sort_by": "price", "sort_order": "desc"})
        assert response.status_code == 200
        data = response.json()
        prices = [item["price"] for item in data["data"]]
        assert prices == sorted(prices, reverse=True)

    def test_list_listings_invalid_page(self, client: TestClient) -> None:
        """Invalid page number returns 422."""
        response = client.get("/api/v1/listings", params={"page": 0})
        assert response.status_code == 422

    def test_list_listings_invalid_page_size(self, client: TestClient) -> None:
        """Invalid page_size returns 422."""
        response = client.get("/api/v1/listings", params={"page_size": 0})
        assert response.status_code == 422

    def test_list_listings_page_size_too_large(self, client: TestClient) -> None:
        """page_size exceeding maximum returns 422."""
        response = client.get("/api/v1/listings", params={"page_size": 101})
        assert response.status_code == 422

    def test_list_listings_response_structure(self, client: TestClient) -> None:
        """Each listing in the response has all expected fields."""
        _create_listing(client, title="Structure Test Item")
        response = client.get("/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0
        first = data["data"][0]
        expected_keys = {
            "id", "seller_id", "title", "description", "category",
            "price", "currency", "status", "tags", "rating",
            "review_count", "created_at", "updated_at",
        }
        assert expected_keys.issubset(set(first.keys()))

    def test_list_listings_total_count(self, client: TestClient) -> None:
        """Total count reflects the number of listings."""
        initial = client.get("/api/v1/listings").json()["total"]
        _create_listing(client, title="Count Test Item")
        after = client.get("/api/v1/listings").json()["total"]
        assert after == initial + 1


# ---------------------------------------------------------------------------
# 2. POST /api/v1/listings  — test_create_listing
# ---------------------------------------------------------------------------

class TestCreateListing:
    """Tests for POST /api/v1/listings."""

    def test_create_listing_success(self, client: TestClient) -> None:
        """Creating a listing with valid data returns 201 and the listing."""
        payload = _sample_listing_payload()
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["price"] == payload["price"]
        assert data["currency"] == payload["currency"]
        assert data["category"] == payload["category"]
        assert data["seller_id"] == payload["seller_id"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["status"] == "active"

    def test_create_listing_minimal_fields(self, client: TestClient) -> None:
        """Creating a listing with only required fields succeeds."""
        payload = {
            "seller_id": "usr_min_001",
            "title": "Minimal Listing",
            "description": "A minimal listing description",
            "category": "video",
            "price": 10.0,
        }
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Listing"
        assert data["price"] == 10.0
        assert data["currency"] == "USD"
        assert data["tags"] == []

    def test_create_listing_with_tags(self, client: TestClient) -> None:
        """Creating a listing with tags stores them correctly."""
        payload = _sample_listing_payload(tags=["tag1", "tag2", "tag3"])
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["tags"]) == 3
        assert "tag1" in data["tags"]

    def test_create_listing_missing_title(self, client: TestClient) -> None:
        """Missing required field 'title' returns 422."""
        payload = _sample_listing_payload()
        del payload["title"]
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_missing_price(self, client: TestClient) -> None:
        """Missing required field 'price' returns 422."""
        payload = _sample_listing_payload()
        del payload["price"]
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_missing_seller_id(self, client: TestClient) -> None:
        """Missing required field 'seller_id' returns 422."""
        payload = _sample_listing_payload()
        del payload["seller_id"]
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_missing_description(self, client: TestClient) -> None:
        """Missing required field 'description' returns 422."""
        payload = _sample_listing_payload()
        del payload["description"]
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_missing_category(self, client: TestClient) -> None:
        """Missing required field 'category' returns 422."""
        payload = _sample_listing_payload()
        del payload["category"]
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_invalid_price_type(self, client: TestClient) -> None:
        """Non-numeric price returns 422."""
        payload = _sample_listing_payload(price="not-a-number")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_negative_price(self, client: TestClient) -> None:
        """Negative price returns 422."""
        payload = _sample_listing_payload(price=-5.0)
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_zero_price(self, client: TestClient) -> None:
        """Zero price returns 422."""
        payload = _sample_listing_payload(price=0)
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_price_too_high(self, client: TestClient) -> None:
        """Price exceeding maximum returns 422."""
        payload = _sample_listing_payload(price=100001.0)
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_empty_title(self, client: TestClient) -> None:
        """Empty title string returns 422."""
        payload = _sample_listing_payload(title="")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_short_title(self, client: TestClient) -> None:
        """Title shorter than 5 characters returns 422."""
        payload = _sample_listing_payload(title="Hi")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_long_title(self, client: TestClient) -> None:
        """Title exceeding 200 characters returns 422."""
        payload = _sample_listing_payload(title="A" * 201)
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_short_description(self, client: TestClient) -> None:
        """Description shorter than 20 characters returns 422."""
        payload = _sample_listing_payload(description="Too short")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_invalid_category(self, client: TestClient) -> None:
        """Invalid category returns 422."""
        payload = _sample_listing_payload(category="invalid_category")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_invalid_currency(self, client: TestClient) -> None:
        """Invalid currency code returns 422."""
        payload = _sample_listing_payload(currency="INVALID")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_lowercase_currency(self, client: TestClient) -> None:
        """Lowercase currency code returns 422."""
        payload = _sample_listing_payload(currency="usd")
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_too_many_tags(self, client: TestClient) -> None:
        """More than 10 tags returns 422."""
        payload = _sample_listing_payload(tags=[f"tag{i}" for i in range(11)])
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_tag_too_long(self, client: TestClient) -> None:
        """Tag exceeding 30 characters returns 422."""
        payload = _sample_listing_payload(tags=["a" * 31])
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 422

    def test_create_listing_response_has_id(self, client: TestClient) -> None:
        """Response contains a unique id field."""
        payload = _sample_listing_payload()
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert isinstance(data["id"], str)

    def test_create_listing_duplicate_title_allowed(self, client: TestClient) -> None:
        """Two listings with the same title can be created."""
        payload = _sample_listing_payload(title="Duplicate Title")
        r1 = client.post("/api/v1/listings", json=payload)
        r2 = client.post("/api/v1/listings", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]

    def test_create_listing_all_valid_categories(self, client: TestClient) -> None:
        """All valid categories are accepted."""
        valid_categories = [
            "video", "social_media", "influencer", "photography",
            "copywriting", "ecommerce", "audio", "consulting", "advertising",
        ]
        for i, category in enumerate(valid_categories):
            payload = _sample_listing_payload(
                title=f"Category Test {i}",
                category=category,
            )
            response = client.post("/api/v1/listings", json=payload)
            assert response.status_code == 201, f"Category '{category}' should be valid"
            assert response.json()["category"] == category

    def test_create_listing_timestamps(self, client: TestClient) -> None:
        """Created listing has valid timestamps."""
        payload = _sample_listing_payload()
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    def test_create_listing_rating_defaults(self, client: TestClient) -> None:
        """New listing has default rating and review_count."""
        payload = _sample_listing_payload()
        response = client.post("/api/v1/listings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 0.0
        assert data["review_count"] == 0


# ---------------------------------------------------------------------------
# 3. GET /api/v1/listings/{id}  — test_get_listing
# ---------------------------------------------------------------------------

class TestGetListing:
    """Tests for GET /api/v1/listings/{id}."""

    def test_get_listing_success(self, client: TestClient) -> None:
        """Getting an existing listing returns 200 with correct data."""
        created = _create_listing(client, title="Get Test Item")
        listing_id = created["id"]

        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == listing_id
        assert data["title"] == "Get Test Item"

    def test_get_listing_not_found(self, client: TestClient) -> None:
        """Getting a non-existent listing returns 404."""
        response = client.get("/api/v1/listings/nonexistent_id_99999")
        assert response.status_code == 404

    def test_get_listing_response_structure(self, client: TestClient) -> None:
        """Response contains all expected fields."""
        created = _create_listing(client, title="Structure Get Test")
        listing_id = created["id"]

        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 200
        data = response.json()
        expected_keys = {
            "id", "seller_id", "title", "description", "category",
            "price", "currency", "status", "tags", "rating",
            "review_count", "created_at", "updated_at",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_get_listing_preserves_data(self, client: TestClient) -> None:
        """Retrieved listing matches the created data."""
        payload = _sample_listing_payload(
            title="Preserve Test",
            description="This description should be preserved exactly",
            price=99.99,
            category="photography",
            tags=["preserve", "test"],
        )
        response = client.post("/api/v1/listings", json=payload)
        created = response.json()
        listing_id = created["id"]

        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["price"] == payload["price"]
        assert data["category"] == payload["category"]
        assert data["seller_id"] == payload["seller_id"]

    def test_get_listing_multiple(self, client: TestClient) -> None:
        """Multiple listings can be retrieved independently."""
        created_1 = _create_listing(client, title="First Item")
        created_2 = _create_listing(client, title="Second Item")

        r1 = client.get(f"/api/v1/listings/{created_1['id']}")
        r2 = client.get(f"/api/v1/listings/{created_2['id']}")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["title"] == "First Item"
        assert r2.json()["title"] == "Second Item"

    def test_get_listing_invalid_id_format(self, client: TestClient) -> None:
        """Getting a listing with special characters in ID returns 404."""
        response = client.get("/api/v1/listings/!@#$%^&*()")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 4. PUT /api/v1/listings/{id}  — test_update_listing
# ---------------------------------------------------------------------------

class TestUpdateListing:
    """Tests for PUT /api/v1/listings/{id}."""

    def test_update_listing_success(self, client: TestClient) -> None:
        """Updating an existing listing returns 200 with updated data."""
        created = _create_listing(client, title="Original Title")
        listing_id = created["id"]

        update_payload = _sample_listing_payload(
            title="Updated Title",
            description="Updated description with sufficient detail",
            price=49.99,
            category="photography",
        )
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == listing_id
        assert data["title"] == "Updated Title"
        assert data["price"] == 49.99
        assert data["category"] == "photography"

    def test_update_listing_not_found(self, client: TestClient) -> None:
        """Updating a non-existent listing returns 404."""
        payload = _sample_listing_payload()
        response = client.put("/api/v1/listings/nonexistent_id_99999", json=payload)
        assert response.status_code == 404

    def test_update_listing_preserves_id(self, client: TestClient) -> None:
        """Update does not change the listing ID."""
        created = _create_listing(client, title="ID Preserve Test")
        listing_id = created["id"]

        update_payload = _sample_listing_payload(title="New Title After Update")
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["id"] == listing_id

    def test_update_listing_preserves_status(self, client: TestClient) -> None:
        """Update preserves the existing status field."""
        created = _create_listing(client, title="Status Preserve Test")
        listing_id = created["id"]
        original_status = created["status"]

        update_payload = _sample_listing_payload(title="Status Test Updated")
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["status"] == original_status

    def test_update_listing_preserves_rating(self, client: TestClient) -> None:
        """Update preserves the existing rating and review_count."""
        created = _create_listing(client, title="Rating Preserve Test")
        listing_id = created["id"]
        original_rating = created["rating"]
        original_review_count = created["review_count"]

        update_payload = _sample_listing_payload(title="Rating Test Updated")
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == original_rating
        assert data["review_count"] == original_review_count

    def test_update_listing_changes_updated_at(self, client: TestClient) -> None:
        """Update changes the updated_at timestamp."""
        created = _create_listing(client, title="Timestamp Test")
        listing_id = created["id"]
        original_updated_at = created["updated_at"]

        update_payload = _sample_listing_payload(title="Timestamp Updated")
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        # updated_at should be different from or equal to original
        assert data["updated_at"] is not None

    def test_update_listing_partial_replacement(self, client: TestClient) -> None:
        """PUT replaces all fields with provided values."""
        created = _create_listing(
            client,
            title="Original Full Title",
            description="Original full description that is long enough",
            tags=["original", "tags"],
        )
        listing_id = created["id"]

        # Update with different tags
        update_payload = _sample_listing_payload(
            title="Completely New Title",
            tags=["new", "tags"],
        )
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Completely New Title"
        assert "new" in data["tags"]
        assert "original" not in data["tags"]

    def test_update_listing_invalid_payload(self, client: TestClient) -> None:
        """Updating with invalid payload returns 422."""
        created = _create_listing(client, title="Invalid Update Test")
        listing_id = created["id"]

        # Missing required fields
        response = client.put(f"/api/v1/listings/{listing_id}", json={"title": "Only Title"})
        assert response.status_code == 422

    def test_update_listing_invalid_category(self, client: TestClient) -> None:
        """Updating with invalid category returns 422."""
        created = _create_listing(client, title="Invalid Category Update")
        listing_id = created["id"]

        update_payload = _sample_listing_payload(category="invalid_category")
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 422

    def test_update_listing_invalid_price(self, client: TestClient) -> None:
        """Updating with invalid price returns 422."""
        created = _create_listing(client, title="Invalid Price Update")
        listing_id = created["id"]

        update_payload = _sample_listing_payload(price=-10.0)
        response = client.put(f"/api/v1/listings/{listing_id}", json=update_payload)
        assert response.status_code == 422

    def test_update_listing_verify_persistence(self, client: TestClient) -> None:
        """Updated listing is persisted and retrievable."""
        created = _create_listing(client, title="Before Update")
        listing_id = created["id"]

        update_payload = _sample_listing_payload(
            title="After Update",
            price=199.99,
            category="ecommerce",
        )
        client.put(f"/api/v1/listings/{listing_id}", json=update_payload)

        # Retrieve and verify
        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "After Update"
        assert data["price"] == 199.99
        assert data["category"] == "ecommerce"


# ---------------------------------------------------------------------------
# 5. DELETE /api/v1/listings/{id}  — test_delete_listing
# ---------------------------------------------------------------------------

class TestDeleteListing:
    """Tests for DELETE /api/v1/listings/{id}."""

    def test_delete_listing_success(self, client: TestClient) -> None:
        """Deleting an existing listing returns 204."""
        created = _create_listing(client, title="Delete Test Item")
        listing_id = created["id"]

        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 204

    def test_delete_listing_not_found(self, client: TestClient) -> None:
        """Deleting a non-existent listing returns 404."""
        response = client.delete("/api/v1/listings/nonexistent_id_99999")
        assert response.status_code == 404

    def test_delete_listing_removes_from_store(self, client: TestClient) -> None:
        """Deleted listing is no longer retrievable."""
        created = _create_listing(client, title="Delete Remove Test")
        listing_id = created["id"]

        # Verify it exists
        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 200

        # Delete it
        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 404

    def test_delete_listing_no_content_response(self, client: TestClient) -> None:
        """Delete response has no content body."""
        created = _create_listing(client, title="No Content Test")
        listing_id = created["id"]

        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 204
        assert response.content == b""

    def test_delete_listing_others_unaffected(self, client: TestClient) -> None:
        """Deleting one listing does not affect others."""
        created_1 = _create_listing(client, title="Keep This Item")
        created_2 = _create_listing(client, title="Delete This Item")
        id_1 = created_1["id"]
        id_2 = created_2["id"]

        # Delete the second listing
        response = client.delete(f"/api/v1/listings/{id_2}")
        assert response.status_code == 204

        # First listing should still exist
        response = client.get(f"/api/v1/listings/{id_1}")
        assert response.status_code == 200
        assert response.json()["title"] == "Keep This Item"

    def test_delete_listing_twice(self, client: TestClient) -> None:
        """Deleting the same listing twice returns 404 on second attempt."""
        created = _create_listing(client, title="Double Delete Test")
        listing_id = created["id"]

        # First delete succeeds
        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 204

        # Second delete returns 404
        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 404

    def test_delete_listing_invalid_id(self, client: TestClient) -> None:
        """Deleting with special characters in ID returns 404."""
        response = client.delete("/api/v1/listings/!@#$%^&*()")
        assert response.status_code == 404

    def test_delete_listing_verify_list_count(self, client: TestClient) -> None:
        """Deleting a listing reduces the total count."""
        created = _create_listing(client, title="Count Delete Test")
        listing_id = created["id"]

        before = client.get("/api/v1/listings").json()["total"]

        response = client.delete(f"/api/v1/listings/{listing_id}")
        assert response.status_code == 204

        after = client.get("/api/v1/listings").json()["total"]
        assert after == before - 1
