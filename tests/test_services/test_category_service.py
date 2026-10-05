"""Tests for CategoryService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from ugc_marketplace.services.category_service import (
    CategoryService,
    CategoryNotFoundError,
    CategoryServiceError,
)


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def category_service(mock_db):
    """Provide a CategoryService instance with mocked DB."""
    return CategoryService(db=mock_db)


@pytest.fixture
def sample_category_data():
    """Provide sample category data."""
    return {
        "id": "category-001",
        "name": "Digital Art",
        "description": "Digital artwork and illustrations",
        "parent_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_child_category_data():
    """Provide sample child category data."""
    return {
        "id": "category-002",
        "name": "Pixel Art",
        "description": "Pixel art creations",
        "parent_id": "category-001",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestGetCategory:
    """Test suite for CategoryService.get_category."""

    def test_get_category_success(
        self, category_service, mock_db, sample_category_data
    ):
        """Test successfully retrieving a category by ID."""
        mock_db.get_category.return_value = sample_category_data

        result = category_service.get_category("category-001")

        assert result is not None
        assert result["id"] == "category-001"
        assert result["name"] == "Digital Art"
        assert result["description"] == "Digital artwork and illustrations"
        mock_db.get_category.assert_called_once_with("category-001")

    def test_get_category_not_found(self, category_service, mock_db):
        """Test retrieving a non-existent category raises CategoryNotFoundError."""
        mock_db.get_category.return_value = None

        with pytest.raises(CategoryNotFoundError) as exc_info:
            category_service.get_category("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_get_category_db_error(self, category_service, mock_db):
        """Test that DB errors are wrapped in CategoryServiceError."""
        mock_db.get_category.side_effect = Exception("DB connection failed")

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.get_category("category-001")

        assert "Failed to retrieve category" in str(exc_info.value)
        assert "category-001" in str(exc_info.value)

    def test_get_category_with_parent(
        self, category_service, mock_db, sample_child_category_data
    ):
        """Test retrieving a child category with parent_id."""
        mock_db.get_category.return_value = sample_child_category_data

        result = category_service.get_category("category-002")

        assert result is not None
        assert result["id"] == "category-002"
        assert result["name"] == "Pixel Art"
        assert result["parent_id"] == "category-001"


class TestListCategories:
    """Test suite for CategoryService.list_categories."""

    def test_list_categories_success(
        self, category_service, mock_db, sample_category_data
    ):
        """Test successfully listing categories."""
        mock_db.list_categories.return_value = [sample_category_data]

        result = category_service.list_categories(
            filters={}, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "category-001"
        mock_db.list_categories.assert_called_once_with(
            filters={}, offset=0, limit=10
        )

    def test_list_categories_with_filters(
        self, category_service, mock_db, sample_category_data
    ):
        """Test listing categories with filter criteria."""
        mock_db.list_categories.return_value = [sample_category_data]
        filters = {"name": "Digital Art", "parent_id": None}

        result = category_service.list_categories(
            filters=filters, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) == 1
        mock_db.list_categories.assert_called_once_with(
            filters=filters, offset=0, limit=10
        )

    def test_list_categories_empty(self, category_service, mock_db):
        """Test listing categories when none exist."""
        mock_db.list_categories.return_value = []

        result = category_service.list_categories(
            filters={}, page=1, page_size=10
        )

        assert result == []

    def test_list_categories_pagination(
        self, category_service, mock_db, sample_category_data
    ):
        """Test listing categories with pagination."""
        mock_db.list_categories.return_value = [sample_category_data]

        result = category_service.list_categories(
            filters={}, page=2, page_size=5
        )

        assert isinstance(result, list)
        mock_db.list_categories.assert_called_once_with(
            filters={}, offset=5, limit=5
        )

    def test_list_categories_page_3(
        self, category_service, mock_db, sample_category_data
    ):
        """Test listing categories on page 3."""
        mock_db.list_categories.return_value = [sample_category_data]

        result = category_service.list_categories(
            filters={}, page=3, page_size=10
        )

        assert isinstance(result, list)
        mock_db.list_categories.assert_called_once_with(
            filters={}, offset=20, limit=10
        )

    def test_list_categories_multiple_results(
        self, category_service, mock_db, sample_category_data, sample_child_category_data
    ):
        """Test listing multiple categories."""
        mock_db.list_categories.return_value = [
            sample_category_data,
            sample_child_category_data,
        ]

        result = category_service.list_categories(
            filters={}, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "category-001"
        assert result[1]["id"] == "category-002"

    def test_list_categories_db_error(self, category_service, mock_db):
        """Test that DB errors are wrapped in CategoryServiceError."""
        mock_db.list_categories.side_effect = Exception("Query failed")

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.list_categories(filters={}, page=1, page_size=10)

        assert "Failed to list categories" in str(exc_info.value)

    def test_list_categories_with_parent_filter(
        self, category_service, mock_db, sample_child_category_data
    ):
        """Test listing categories filtered by parent_id."""
        mock_db.list_categories.return_value = [sample_child_category_data]
        filters = {"parent_id": "category-001"}

        result = category_service.list_categories(
            filters=filters, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["parent_id"] == "category-001"
        mock_db.list_categories.assert_called_once_with(
            filters=filters, offset=0, limit=10
        )


class TestCreateCategory:
    """Test suite for CategoryService.create_category."""

    def test_create_category_success(self, category_service, mock_db):
        """Test successfully creating a new category."""
        new_category = {
            "name": "Photography",
            "description": "Photography category",
            "parent_id": None,
        }
        created_category = {
            "id": "category-new",
            "name": "Photography",
            "description": "Photography category",
            "parent_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_db.create_category.return_value = created_category

        result = category_service.create_category(new_category)

        assert result is not None
        assert result["id"] == "category-new"
        assert result["name"] == "Photography"
        assert result["description"] == "Photography category"
        mock_db.create_category.assert_called_once_with(new_category)

    def test_create_category_with_parent(self, category_service, mock_db):
        """Test creating a child category with parent_id."""
        new_category = {
            "name": "Landscape Photography",
            "description": "Landscape photos",
            "parent_id": "category-001",
        }
        created_category = {
            "id": "category-child",
            "name": "Landscape Photography",
            "description": "Landscape photos",
            "parent_id": "category-001",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_db.create_category.return_value = created_category

        result = category_service.create_category(new_category)

        assert result is not None
        assert result["parent_id"] == "category-001"
        mock_db.create_category.assert_called_once_with(new_category)

    def test_create_category_minimal_data(self, category_service, mock_db):
        """Test creating a category with minimal required data."""
        new_category = {"name": "Music"}
        created_category = {
            "id": "category-music",
            "name": "Music",
            "description": None,
            "parent_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_db.create_category.return_value = created_category

        result = category_service.create_category(new_category)

        assert result is not None
        assert result["name"] == "Music"
        assert result["description"] is None

    def test_create_category_db_error(self, category_service, mock_db):
        """Test that DB errors are wrapped in CategoryServiceError."""
        mock_db.create_category.side_effect = Exception("Insert failed")

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.create_category({"name": "Test"})

        assert "Failed to create category" in str(exc_info.value)

    def test_create_category_duplicate_name(self, category_service, mock_db):
        """Test creating a category with duplicate name raises error."""
        mock_db.create_category.side_effect = Exception(
            "Duplicate key value violates unique constraint"
        )

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.create_category({"name": "Digital Art"})

        assert "Failed to create category" in str(exc_info.value)


class TestUpdateCategory:
    """Test suite for CategoryService.update_category."""

    def test_update_category_success(
        self, category_service, mock_db, sample_category_data
    ):
        """Test successfully updating a category."""
        mock_db.update_category.return_value = {
            **sample_category_data,
            "name": "Updated Digital Art",
            "description": "Updated description",
        }

        updates = {"name": "Updated Digital Art", "description": "Updated description"}
        result = category_service.update_category("category-001", updates)

        assert result is not None
        assert result["id"] == "category-001"
        assert result["name"] == "Updated Digital Art"
        assert result["description"] == "Updated description"
        mock_db.update_category.assert_called_once_with("category-001", updates)

    def test_update_category_partial_update(
        self, category_service, mock_db, sample_category_data
    ):
        """Test updating only specific fields of a category."""
        mock_db.update_category.return_value = {
            **sample_category_data,
            "name": "New Name",
        }

        updates = {"name": "New Name"}
        result = category_service.update_category("category-001", updates)

        assert result is not None
        assert result["name"] == "New Name"
        assert result["description"] == "Digital artwork and illustrations"
        mock_db.update_category.assert_called_once_with("category-001", updates)

    def test_update_category_not_found(self, category_service, mock_db):
        """Test updating a non-existent category raises CategoryNotFoundError."""
        mock_db.update_category.return_value = None

        with pytest.raises(CategoryNotFoundError) as exc_info:
            category_service.update_category("nonexistent", {"name": "New"})

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_update_category_db_error(self, category_service, mock_db):
        """Test that DB errors are wrapped in CategoryServiceError."""
        mock_db.update_category.side_effect = Exception("Update failed")

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.update_category("category-001", {"name": "New"})

        assert "Failed to update category" in str(exc_info.value)
        assert "category-001" in str(exc_info.value)

    def test_update_category_change_parent(
        self, category_service, mock_db, sample_child_category_data
    ):
        """Test updating a category's parent_id."""
        mock_db.update_category.return_value = {
            **sample_child_category_data,
            "parent_id": "category-003",
        }

        updates = {"parent_id": "category-003"}
        result = category_service.update_category("category-002", updates)

        assert result is not None
        assert result["parent_id"] == "category-003"
        mock_db.update_category.assert_called_once_with("category-002", updates)

    def test_update_category_remove_parent(
        self, category_service, mock_db, sample_child_category_data
    ):
        """Test removing a category's parent (making it a root category)."""
        mock_db.update_category.return_value = {
            **sample_child_category_data,
            "parent_id": None,
        }

        updates = {"parent_id": None}
        result = category_service.update_category("category-002", updates)

        assert result is not None
        assert result["parent_id"] is None
        mock_db.update_category.assert_called_once_with("category-002", updates)


class TestDeleteCategory:
    """Test suite for CategoryService.delete_category."""

    def test_delete_category_success(self, category_service, mock_db):
        """Test successfully deleting a category."""
        mock_db.delete_category.return_value = True

        result = category_service.delete_category("category-001")

        assert result is True
        mock_db.delete_category.assert_called_once_with("category-001")

    def test_delete_category_not_found(self, category_service, mock_db):
        """Test deleting a non-existent category raises CategoryNotFoundError."""
        mock_db.delete_category.return_value = False

        with pytest.raises(CategoryNotFoundError) as exc_info:
            category_service.delete_category("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_delete_category_db_error(self, category_service, mock_db):
        """Test that DB errors are wrapped in CategoryServiceError."""
        mock_db.delete_category.side_effect = Exception("Delete failed")

        with pytest.raises(CategoryServiceError) as exc_info:
            category_service.delete_category("category-001")

        assert "Failed to delete category" in str(exc_info.value)
        assert "category-001" in str(exc_info.value)

    def test_delete_category_cascade(
        self, category_service, mock_db, sample_child_category_data
    ):
        """Test deleting a parent category (should cascade to children)."""
        mock_db.delete_category.return_value = True

        result = category_service.delete_category("category-001")

        assert result is True
        mock_db.delete_category.assert_called_once_with("category-001")

    def test_delete_category_returns_true_on_success(
        self, category_service, mock_db
    ):
        """Test that delete returns exactly True on success."""
        mock_db.delete_category.return_value = True

        result = category_service.delete_category("category-001")

        assert result is True
        assert isinstance(result, bool)
