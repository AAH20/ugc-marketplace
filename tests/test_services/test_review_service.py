"""Tests for ReviewService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ugc_marketplace.services.review_service import (
    get_review,
    list_reviews,
    create_review,
    update_review,
    delete_review,
    ReviewNotFoundError,
    ReviewValidationError,
)


@pytest.fixture
def sample_review_data():
    """Provide sample review data."""
    return {
        "id": "review-001",
        "transaction_id": "txn-001",
        "reviewer_id": "user-001",
        "rating": 5,
        "comment": "Excellent product!",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_review_list():
    """Provide a list of sample reviews."""
    return [
        {
            "id": f"review-{i:03d}",
            "transaction_id": f"txn-{i:03d}",
            "reviewer_id": f"user-{i:03d}",
            "rating": (i % 5) + 1,
            "comment": f"Comment {i}",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        for i in range(5)
    ]


class TestGetReview:
    """Test suite for get_review function."""

    def test_get_review_returns_review(self, sample_review_data):
        """Test that get_review returns a review when found."""
        with patch("ugc_marketplace.services.review_service.get_review") as mock_get:
            mock_get.return_value = sample_review_data

            result = get_review("review-001")

            assert result is not None
            assert result["id"] == "review-001"
            assert result["rating"] == 5

    def test_get_review_not_found(self):
        """Test that get_review raises ReviewNotFoundError when review doesn't exist."""
        with patch("ugc_marketplace.services.review_service.get_review") as mock_get:
            mock_get.side_effect = ReviewNotFoundError("Review not found")

            with pytest.raises(ReviewNotFoundError):
                get_review("nonexistent-id")

    def test_get_review_empty_id(self):
        """Test that get_review raises ReviewValidationError for empty ID."""
        with pytest.raises(ReviewValidationError):
            get_review("")

    def test_get_review_none_id(self):
        """Test that get_review raises ReviewValidationError for None ID."""
        with pytest.raises(ReviewValidationError):
            get_review(None)

    def test_get_review_non_string_id(self):
        """Test that get_review raises ReviewValidationError for non-string ID."""
        with pytest.raises(ReviewValidationError):
            get_review(123)

    def test_get_review_invalid_id_type(self):
        """Test that get_review raises ReviewValidationError for invalid ID type."""
        with pytest.raises(ReviewValidationError):
            get_review(["invalid"])


class TestListReviews:
    """Test suite for list_reviews function."""

    def test_list_reviews_returns_list(self, sample_review_list):
        """Test that list_reviews returns a list of reviews."""
        with patch("ugc_marketplace.services.review_service.list_reviews") as mock_list:
            mock_list.return_value = sample_review_list

            result = list_reviews(filters={}, page=1, page_size=10)

            assert isinstance(result, list)
            assert len(result) == 5

    def test_list_reviews_empty(self):
        """Test that list_reviews returns empty list when no reviews exist."""
        with patch("ugc_marketplace.services.review_service.list_reviews") as mock_list:
            mock_list.return_value = []

            result = list_reviews(filters={}, page=1, page_size=10)

            assert result == []

    def test_list_reviews_with_filters(self, sample_review_list):
        """Test that list_reviews applies filters correctly."""
        with patch("ugc_marketplace.services.review_service.list_reviews") as mock_list:
            mock_list.return_value = [r for r in sample_review_list if r["reviewer_id"] == "user-001"]

            result = list_reviews(filters={"reviewer_id": "user-001"}, page=1, page_size=10)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["reviewer_id"] == "user-001"

    def test_list_reviews_pagination(self, sample_review_list):
        """Test that list_reviews respects pagination parameters."""
        with patch("ugc_marketplace.services.review_service.list_reviews") as mock_list:
            mock_list.return_value = sample_review_list[:2]

            result = list_reviews(filters={}, page=1, page_size=2)

            assert isinstance(result, list)
            assert len(result) == 2

    def test_list_reviews_invalid_page(self):
        """Test that list_reviews raises ReviewValidationError for invalid page."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page=0, page_size=10)

    def test_list_reviews_invalid_page_size(self):
        """Test that list_reviews raises ReviewValidationError for invalid page_size."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page=1, page_size=0)

    def test_list_reviews_negative_page(self):
        """Test that list_reviews raises ReviewValidationError for negative page."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page=-1, page_size=10)

    def test_list_reviews_negative_page_size(self):
        """Test that list_reviews raises ReviewValidationError for negative page_size."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page=1, page_size=-5)

    def test_list_reviews_non_dict_filters(self):
        """Test that list_reviews raises ReviewValidationError for non-dict filters."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters="invalid", page=1, page_size=10)

    def test_list_reviews_non_int_page(self):
        """Test that list_reviews raises ReviewValidationError for non-integer page."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page="1", page_size=10)

    def test_list_reviews_non_int_page_size(self):
        """Test that list_reviews raises ReviewValidationError for non-integer page_size."""
        with pytest.raises(ReviewValidationError):
            list_reviews(filters={}, page=1, page_size="10")


class TestCreateReview:
    """Test suite for create_review function."""

    def test_create_review_returns_review(self, sample_review_data):
        """Test that create_review returns the created review."""
        with patch("ugc_marketplace.services.review_service.create_review") as mock_create:
            mock_create.return_value = sample_review_data

            result = create_review(sample_review_data)

            assert result is not None
            assert result["id"] == "review-001"
            assert result["rating"] == 5

    def test_create_review_with_minimal_data(self):
        """Test that create_review works with minimal required data."""
        minimal_data = {
            "transaction_id": "txn-001",
            "reviewer_id": "user-001",
            "rating": 4,
        }
        with patch("ugc_marketplace.services.review_service.create_review") as mock_create:
            mock_create.return_value = {**minimal_data, "id": "review-new"}

            result = create_review(minimal_data)

            assert result is not None
            assert result["transaction_id"] == "txn-001"
            assert result["rating"] == 4

    def test_create_review_non_dict_data(self):
        """Test that create_review raises ReviewValidationError for non-dict data."""
        with pytest.raises(ReviewValidationError):
            create_review("invalid")

    def test_create_review_list_data(self):
        """Test that create_review raises ReviewValidationError for list data."""
        with pytest.raises(ReviewValidationError):
            create_review([1, 2, 3])

    def test_create_review_none_data(self):
        """Test that create_review raises ReviewValidationError for None data."""
        with pytest.raises(ReviewValidationError):
            create_review(None)

    def test_create_review_preserves_all_fields(self, sample_review_data):
        """Test that create_review preserves all provided fields."""
        with patch("ugc_marketplace.services.review_service.create_review") as mock_create:
            mock_create.return_value = sample_review_data

            result = create_review(sample_review_data)

            assert result["id"] == sample_review_data["id"]
            assert result["transaction_id"] == sample_review_data["transaction_id"]
            assert result["reviewer_id"] == sample_review_data["reviewer_id"]
            assert result["rating"] == sample_review_data["rating"]
            assert result["comment"] == sample_review_data["comment"]


class TestUpdateReview:
    """Test suite for update_review function."""

    def test_update_review_returns_updated_review(self, sample_review_data):
        """Test that update_review returns the updated review."""
        updated_data = {**sample_review_data, "rating": 3, "comment": "Updated comment"}
        with patch("ugc_marketplace.services.review_service.update_review") as mock_update:
            mock_update.return_value = updated_data

            result = update_review("review-001", {"rating": 3, "comment": "Updated comment"})

            assert result is not None
            assert result["rating"] == 3
            assert result["comment"] == "Updated comment"

    def test_update_review_not_found(self):
        """Test that update_review raises ReviewNotFoundError when review doesn't exist."""
        with patch("ugc_marketplace.services.review_service.update_review") as mock_update:
            mock_update.side_effect = ReviewNotFoundError("Review not found")

            with pytest.raises(ReviewNotFoundError):
                update_review("nonexistent-id", {"rating": 3})

    def test_update_review_empty_id(self):
        """Test that update_review raises ReviewValidationError for empty ID."""
        with pytest.raises(ReviewValidationError):
            update_review("", {"rating": 3})

    def test_update_review_none_id(self):
        """Test that update_review raises ReviewValidationError for None ID."""
        with pytest.raises(ReviewValidationError):
            update_review(None, {"rating": 3})

    def test_update_review_non_string_id(self):
        """Test that update_review raises ReviewValidationError for non-string ID."""
        with pytest.raises(ReviewValidationError):
            update_review(123, {"rating": 3})

    def test_update_review_non_dict_data(self):
        """Test that update_review raises ReviewValidationError for non-dict data."""
        with pytest.raises(ReviewValidationError):
            update_review("review-001", "invalid")

    def test_update_review_none_data(self):
        """Test that update_review raises ReviewValidationError for None data."""
        with pytest.raises(ReviewValidationError):
            update_review("review-001", None)

    def test_update_review_partial_update(self, sample_review_data):
        """Test that update_review handles partial updates correctly."""
        with patch("ugc_marketplace.services.review_service.update_review") as mock_update:
            mock_update.return_value = {**sample_review_data, "rating": 2}

            result = update_review("review-001", {"rating": 2})

            assert result is not None
            assert result["rating"] == 2
            # Other fields should be preserved
            assert result["transaction_id"] == sample_review_data["transaction_id"]


class TestDeleteReview:
    """Test suite for delete_review function."""

    def test_delete_review_returns_true(self):
        """Test that delete_review returns True on successful deletion."""
        with patch("ugc_marketplace.services.review_service.delete_review") as mock_delete:
            mock_delete.return_value = True

            result = delete_review("review-001")

            assert result is True

    def test_delete_review_not_found(self):
        """Test that delete_review raises ReviewNotFoundError when review doesn't exist."""
        with patch("ugc_marketplace.services.review_service.delete_review") as mock_delete:
            mock_delete.side_effect = ReviewNotFoundError("Review not found")

            with pytest.raises(ReviewNotFoundError):
                delete_review("nonexistent-id")

    def test_delete_review_empty_id(self):
        """Test that delete_review raises ReviewValidationError for empty ID."""
        with pytest.raises(ReviewValidationError):
            delete_review("")

    def test_delete_review_none_id(self):
        """Test that delete_review raises ReviewValidationError for None ID."""
        with pytest.raises(ReviewValidationError):
            delete_review(None)

    def test_delete_review_non_string_id(self):
        """Test that delete_review raises ReviewValidationError for non-string ID."""
        with pytest.raises(ReviewValidationError):
            delete_review(123)

    def test_delete_review_invalid_id_type(self):
        """Test that delete_review raises ReviewValidationError for invalid ID type."""
        with pytest.raises(ReviewValidationError):
            delete_review({"id": "review-001"})
