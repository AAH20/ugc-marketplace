"""Tests for TagService."""

import pytest
from unittest.mock import MagicMock

from ugc_marketplace.services.tag_service import (
    TagService,
    TagNotFoundError,
    TagServiceError,
)


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def tag_service(mock_db):
    """Provide a TagService instance with mocked DB."""
    return TagService(db=mock_db)


@pytest.fixture
def sample_tag_data():
    """Provide sample tag data."""
    return {
        "id": "tag-001",
        "name": "art",
        "description": "Art-related content",
        "color": "#FF5733",
        "is_active": True,
    }


@pytest.fixture
def sample_tags_list():
    """Provide a list of sample tags."""
    return [
        {"id": "tag-001", "name": "art", "description": "Art content", "color": "#FF5733", "is_active": True},
        {"id": "tag-002", "name": "music", "description": "Music content", "color": "#33FF57", "is_active": True},
        {"id": "tag-003", "name": "photography", "description": "Photo content", "color": "#3357FF", "is_active": False},
    ]


class TestGetTag:
    """Test suite for TagService.get_tag."""

    def test_get_tag_success(self, tag_service, mock_db, sample_tag_data):
        """Test successfully retrieving a tag by ID."""
        mock_db.get_tag.return_value = sample_tag_data

        result = tag_service.get_tag("tag-001")

        assert result is not None
        assert result["id"] == "tag-001"
        assert result["name"] == "art"
        assert result["description"] == "Art-related content"
        assert result["color"] == "#FF5733"
        assert result["is_active"] is True
        mock_db.get_tag.assert_called_once_with("tag-001")

    def test_get_tag_not_found(self, tag_service, mock_db):
        """Test retrieving a non-existent tag raises TagNotFoundError."""
        mock_db.get_tag.return_value = None

        with pytest.raises(TagNotFoundError, match="Tag with ID 'nonexistent' not found"):
            tag_service.get_tag("nonexistent")

        mock_db.get_tag.assert_called_once_with("nonexistent")

    def test_get_tag_db_error(self, tag_service, mock_db):
        """Test that database errors are wrapped in TagServiceError."""
        mock_db.get_tag.side_effect = Exception("Database connection failed")

        with pytest.raises(TagServiceError, match="Failed to get tag"):
            tag_service.get_tag("tag-001")

    def test_get_tag_without_db(self):
        """Test get_tag with no database returns TagNotFoundError."""
        service = TagService(db=None)

        with pytest.raises(TagNotFoundError):
            service.get_tag("tag-001")

    def test_get_tag_returns_dict_copy(self, tag_service, mock_db, sample_tag_data):
        """Test that get_tag returns a dict copy, not the original object."""
        mock_db.get_tag.return_value = sample_tag_data

        result = tag_service.get_tag("tag-001")

        assert isinstance(result, dict)
        assert result is not sample_tag_data


class TestListTags:
    """Test suite for TagService.list_tags."""

    def test_list_tags_success(self, tag_service, mock_db, sample_tags_list):
        """Test successfully listing tags with pagination."""
        mock_db.list_tags.return_value = sample_tags_list

        result = tag_service.list_tags(filters={}, page=1, page_size=10)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["name"] == "art"
        assert result[1]["name"] == "music"
        assert result[2]["name"] == "photography"
        mock_db.list_tags.assert_called_once_with(filters={}, offset=0, limit=10)

    def test_list_tags_with_filters(self, tag_service, mock_db, sample_tags_list):
        """Test listing tags with filter criteria."""
        mock_db.list_tags.return_value = [sample_tags_list[0]]

        filters = {"name": "art", "is_active": True}
        result = tag_service.list_tags(filters=filters, page=1, page_size=10)

        assert len(result) == 1
        assert result[0]["name"] == "art"
        mock_db.list_tags.assert_called_once_with(filters=filters, offset=0, limit=10)

    def test_list_tags_empty_result(self, tag_service, mock_db):
        """Test listing tags when no tags match."""
        mock_db.list_tags.return_value = []

        result = tag_service.list_tags(filters={"name": "nonexistent"}, page=1, page_size=10)

        assert result == []
        assert isinstance(result, list)

    def test_list_tags_pagination(self, tag_service, mock_db, sample_tags_list):
        """Test listing tags with different page numbers."""
        mock_db.list_tags.return_value = sample_tags_list[:2]

        result = tag_service.list_tags(filters={}, page=2, page_size=2)

        assert len(result) == 2
        mock_db.list_tags.assert_called_once_with(filters={}, offset=2, limit=2)

    def test_list_tags_page_zero_raises_error(self, tag_service, mock_db):
        """Test that page < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            tag_service.list_tags(filters={}, page=0, page_size=10)

    def test_list_tags_negative_page_raises_error(self, tag_service, mock_db):
        """Test that negative page raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            tag_service.list_tags(filters={}, page=-1, page_size=10)

    def test_list_tags_page_size_zero_raises_error(self, tag_service, mock_db):
        """Test that page_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            tag_service.list_tags(filters={}, page=1, page_size=0)

    def test_list_tags_negative_page_size_raises_error(self, tag_service, mock_db):
        """Test that negative page_size raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            tag_service.list_tags(filters={}, page=1, page_size=-5)

    def test_list_tags_db_error(self, tag_service, mock_db):
        """Test that database errors are wrapped in TagServiceError."""
        mock_db.list_tags.side_effect = Exception("Query timeout")

        with pytest.raises(TagServiceError, match="Failed to list tags"):
            tag_service.list_tags(filters={}, page=1, page_size=10)

    def test_list_tags_without_db(self):
        """Test list_tags with no database returns empty list."""
        service = TagService(db=None)

        result = service.list_tags(filters={}, page=1, page_size=10)

        assert result == []

    def test_list_tags_returns_dict_copies(self, tag_service, mock_db, sample_tags_list):
        """Test that list_tags returns dict copies."""
        mock_db.list_tags.return_value = sample_tags_list

        result = tag_service.list_tags(filters={}, page=1, page_size=10)

        for i, tag in enumerate(result):
            assert isinstance(tag, dict)
            assert tag is not sample_tags_list[i]


class TestCreateTag:
    """Test suite for TagService.create_tag."""

    def test_create_tag_success(self, tag_service, mock_db, sample_tag_data):
        """Test successfully creating a new tag."""
        mock_db.create_tag.return_value = sample_tag_data

        result = tag_service.create_tag(sample_tag_data)

        assert result is not None
        assert result["id"] == "tag-001"
        assert result["name"] == "art"
        assert result["description"] == "Art-related content"
        mock_db.create_tag.assert_called_once_with(sample_tag_data)

    def test_create_tag_minimal_data(self, tag_service, mock_db):
        """Test creating a tag with minimal required data."""
        minimal_data = {"name": "new-tag"}
        mock_db.create_tag.return_value = {"id": "tag-002", "name": "new-tag"}

        result = tag_service.create_tag(minimal_data)

        assert result is not None
        assert result["name"] == "new-tag"
        mock_db.create_tag.assert_called_once_with(minimal_data)

    def test_create_tag_missing_name_raises_error(self, tag_service, mock_db):
        """Test that creating a tag without name raises ValueError."""
        with pytest.raises(ValueError, match="Tag data must include a 'name' field"):
            tag_service.create_tag({"description": "no name"})

    def test_create_tag_empty_data_raises_error(self, tag_service, mock_db):
        """Test that creating a tag with empty data raises ValueError."""
        with pytest.raises(ValueError, match="Tag data must include a 'name' field"):
            tag_service.create_tag({})

    def test_create_tag_none_data_raises_error(self, tag_service, mock_db):
        """Test that creating a tag with None data raises ValueError."""
        with pytest.raises(ValueError, match="Tag data must include a 'name' field"):
            tag_service.create_tag(None)

    def test_create_tag_db_error(self, tag_service, mock_db):
        """Test that database errors are wrapped in TagServiceError."""
        mock_db.create_tag.side_effect = Exception("Duplicate key violation")

        with pytest.raises(TagServiceError, match="Failed to create tag"):
            tag_service.create_tag({"name": "art"})

    def test_create_tag_without_db(self):
        """Test create_tag with no database returns the input data."""
        service = TagService(db=None)
        data = {"name": "art", "description": "Art content"}

        result = service.create_tag(data)

        assert result is not None
        assert result["name"] == "art"
        assert result["description"] == "Art content"

    def test_create_tag_with_all_fields(self, tag_service, mock_db):
        """Test creating a tag with all possible fields."""
        full_data = {
            "name": "premium",
            "description": "Premium content tag",
            "color": "#FFD700",
            "is_active": True,
            "metadata": {"priority": 1},
        }
        mock_db.create_tag.return_value = {"id": "tag-003", **full_data}

        result = tag_service.create_tag(full_data)

        assert result["name"] == "premium"
        assert result["color"] == "#FFD700"
        assert result["metadata"] == {"priority": 1}


class TestUpdateTag:
    """Test suite for TagService.update_tag."""

    def test_update_tag_success(self, tag_service, mock_db, sample_tag_data):
        """Test successfully updating a tag."""
        mock_db.get_tag.return_value = sample_tag_data
        updated_data = {"id": "tag-001", "name": "fine-art", "description": "Fine art content"}
        mock_db.update_tag.return_value = updated_data

        result = tag_service.update_tag("tag-001", {"name": "fine-art", "description": "Fine art content"})

        assert result is not None
        assert result["name"] == "fine-art"
        assert result["description"] == "Fine art content"
        mock_db.get_tag.assert_called_once_with("tag-001")
        mock_db.update_tag.assert_called_once()

    def test_update_tag_partial_update(self, tag_service, mock_db, sample_tag_data):
        """Test updating only specific fields of a tag."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.update_tag.return_value = {**sample_tag_data, "name": "updated-art"}

        result = tag_service.update_tag("tag-001", {"name": "updated-art"})

        assert result["name"] == "updated-art"
        assert result["description"] == "Art-related content"  # unchanged

    def test_update_tag_not_found(self, tag_service, mock_db):
        """Test updating a non-existent tag raises TagNotFoundError."""
        mock_db.get_tag.return_value = None

        with pytest.raises(TagNotFoundError, match="Tag with ID 'nonexistent' not found"):
            tag_service.update_tag("nonexistent", {"name": "new-name"})

    def test_update_tag_db_error_on_get(self, tag_service, mock_db):
        """Test that database errors during get are wrapped in TagServiceError."""
        mock_db.get_tag.side_effect = Exception("Connection lost")

        with pytest.raises(TagServiceError, match="Failed to update tag"):
            tag_service.update_tag("tag-001", {"name": "new-name"})

    def test_update_tag_db_error_on_update(self, tag_service, mock_db, sample_tag_data):
        """Test that database errors during update are wrapped in TagServiceError."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.update_tag.side_effect = Exception("Write conflict")

        with pytest.raises(TagServiceError, match="Failed to update tag"):
            tag_service.update_tag("tag-001", {"name": "new-name"})

    def test_update_tag_without_db(self):
        """Test update_tag with no database raises TagNotFoundError."""
        service = TagService(db=None)

        with pytest.raises(TagNotFoundError):
            service.update_tag("tag-001", {"name": "new-name"})

    def test_update_tag_preserves_other_fields(self, tag_service, mock_db, sample_tag_data):
        """Test that updating one field preserves other fields."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.update_tag.return_value = {
            **sample_tag_data,
            "name": "new-name",
            "color": "#000000",
        }

        result = tag_service.update_tag("tag-001", {"name": "new-name", "color": "#000000"})

        assert result["name"] == "new-name"
        assert result["color"] == "#000000"
        assert result["description"] == "Art-related content"
        assert result["is_active"] is True


class TestDeleteTag:
    """Test suite for TagService.delete_tag."""

    def test_delete_tag_success(self, tag_service, mock_db, sample_tag_data):
        """Test successfully deleting a tag."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.delete_tag.return_value = None

        result = tag_service.delete_tag("tag-001")

        assert result is True
        mock_db.get_tag.assert_called_once_with("tag-001")
        mock_db.delete_tag.assert_called_once_with("tag-001")

    def test_delete_tag_not_found(self, tag_service, mock_db):
        """Test deleting a non-existent tag raises TagNotFoundError."""
        mock_db.get_tag.return_value = None

        with pytest.raises(TagNotFoundError, match="Tag with ID 'nonexistent' not found"):
            tag_service.delete_tag("nonexistent")

    def test_delete_tag_db_error_on_get(self, tag_service, mock_db):
        """Test that database errors during get are wrapped in TagServiceError."""
        mock_db.get_tag.side_effect = Exception("Connection lost")

        with pytest.raises(TagServiceError, match="Failed to delete tag"):
            tag_service.delete_tag("tag-001")

    def test_delete_tag_db_error_on_delete(self, tag_service, mock_db, sample_tag_data):
        """Test that database errors during delete are wrapped in TagServiceError."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.delete_tag.side_effect = Exception("Foreign key constraint")

        with pytest.raises(TagServiceError, match="Failed to delete tag"):
            tag_service.delete_tag("tag-001")

    def test_delete_tag_without_db(self):
        """Test delete_tag with no database raises TagNotFoundError."""
        service = TagService(db=None)

        with pytest.raises(TagNotFoundError):
            service.delete_tag("tag-001")

    def test_delete_tag_returns_true(self, tag_service, mock_db, sample_tag_data):
        """Test that successful deletion returns exactly True."""
        mock_db.get_tag.return_value = sample_tag_data
        mock_db.delete_tag.return_value = None

        result = tag_service.delete_tag("tag-001")

        assert result is True
        assert type(result) is bool
