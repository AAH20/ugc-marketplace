"""Tests for ContentService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from ugc_marketplace.services.content_service import ContentService


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def content_service(mock_db):
    """Provide a ContentService instance with mocked DB."""
    return ContentService(db=mock_db)


@pytest.fixture
def sample_content_data():
    """Provide sample content data."""
    return {
        "id": "content-001",
        "creator_id": "creator-001",
        "title": "Test Content",
        "description": "A test content piece",
        "content_type": "image",
        "media_url": "https://example.com/media.png",
        "status": "draft",
        "tags": ["test", "sample"],
        "view_count": 0,
        "like_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestContentService:
    """Test suite for ContentService."""

    def test_create_content(self, content_service, mock_db, sample_content_data):
        """Test creating new content."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        content = content_service.create_content(sample_content_data)

        assert content is not None
        assert content["title"] == "Test Content"
        assert content["creator_id"] == "creator-001"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_content_by_id(self, content_service, mock_db, sample_content_data):
        """Test retrieving content by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data

        content = content_service.get_content_by_id("content-001")

        assert content is not None
        assert content["id"] == "content-001"
        assert content["title"] == "Test Content"

    def test_get_content_by_id_not_found(self, content_service, mock_db):
        """Test retrieving non-existent content returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        content = content_service.get_content_by_id("nonexistent")

        assert content is None

    def test_list_content_by_creator(self, content_service, mock_db, sample_content_data):
        """Test listing content by creator ID."""
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_content_data
        ]

        contents = content_service.list_content_by_creator("creator-001", skip=0, limit=10)

        assert isinstance(contents, list)
        assert len(contents) == 1

    def test_update_content(self, content_service, mock_db, sample_content_data):
        """Test updating content."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.commit.return_value = None

        updates = {"title": "Updated Title", "status": "published"}
        updated = content_service.update_content("content-001", updates)

        assert updated is not None
        mock_db.commit.assert_called_once()

    def test_update_content_not_found(self, content_service, mock_db):
        """Test updating non-existent content returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = content_service.update_content("nonexistent", {"title": "new"})

        assert result is None

    def test_delete_content(self, content_service, mock_db, sample_content_data):
        """Test deleting content."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = content_service.delete_content("content-001")

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_content_not_found(self, content_service, mock_db):
        """Test deleting non-existent content returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = content_service.delete_content("nonexistent")

        assert result is False

    def test_publish_content(self, content_service, mock_db, sample_content_data):
        """Test publishing draft content."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.commit.return_value = None

        result = content_service.publish_content("content-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_archive_content(self, content_service, mock_db, sample_content_data):
        """Test archiving content."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.commit.return_value = None

        result = content_service.archive_content("content-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_increment_view_count(self, content_service, mock_db, sample_content_data):
        """Test incrementing view count."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.commit.return_value = None

        result = content_service.increment_view_count("content-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_increment_like_count(self, content_service, mock_db, sample_content_data):
        """Test incrementing like count."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_content_data
        mock_db.commit.return_value = None

        result = content_service.increment_like_count("content-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_list_content_by_status(self, content_service, mock_db, sample_content_data):
        """Test listing content filtered by status."""
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_content_data
        ]

        contents = content_service.list_content_by_status("draft", skip=0, limit=10)

        assert isinstance(contents, list)
        assert len(contents) == 1

    def test_search_content(self, content_service, mock_db, sample_content_data):
        """Test searching content by title or tags."""
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_content_data]

        results = content_service.search_content("test")

        assert isinstance(results, list)
        assert len(results) == 1
