"""Tests for CreatorService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ugc_marketplace.services.creator_service import CreatorService


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def creator_service(mock_db):
    """Provide a CreatorService instance with mocked DB."""
    return CreatorService(db=mock_db)


@pytest.fixture
def sample_creator_data():
    """Provide sample creator data."""
    return {
        "id": "creator-001",
        "username": "test_creator",
        "email": "creator@example.com",
        "display_name": "Test Creator",
        "bio": "A test creator",
        "avatar_url": "https://example.com/avatar.png",
        "verified": False,
        "follower_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestCreatorService:
    """Test suite for CreatorService."""

    def test_create_creator(self, creator_service, mock_db, sample_creator_data):
        """Test creating a new creator."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        creator = creator_service.create_creator(sample_creator_data)

        assert creator is not None
        assert creator["username"] == "test_creator"
        assert creator["email"] == "creator@example.com"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_creator_by_id(self, creator_service, mock_db, sample_creator_data):
        """Test retrieving a creator by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data

        creator = creator_service.get_creator_by_id("creator-001")

        assert creator is not None
        assert creator["id"] == "creator-001"
        assert creator["username"] == "test_creator"

    def test_get_creator_by_id_not_found(self, creator_service, mock_db):
        """Test retrieving a non-existent creator returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        creator = creator_service.get_creator_by_id("nonexistent")

        assert creator is None

    def test_get_creator_by_username(self, creator_service, mock_db, sample_creator_data):
        """Test retrieving a creator by username."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data

        creator = creator_service.get_creator_by_username("test_creator")

        assert creator is not None
        assert creator["username"] == "test_creator"

    def test_update_creator(self, creator_service, mock_db, sample_creator_data):
        """Test updating a creator's profile."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data
        mock_db.commit.return_value = None

        updates = {"display_name": "Updated Name", "bio": "Updated bio"}
        updated = creator_service.update_creator("creator-001", updates)

        assert updated is not None
        mock_db.commit.assert_called_once()

    def test_update_creator_not_found(self, creator_service, mock_db):
        """Test updating a non-existent creator returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.update_creator("nonexistent", {"bio": "new"})

        assert result is None

    def test_delete_creator(self, creator_service, mock_db, sample_creator_data):
        """Test deleting a creator."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = creator_service.delete_creator("creator-001")

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_creator_not_found(self, creator_service, mock_db):
        """Test deleting a non-existent creator returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.delete_creator("nonexistent")

        assert result is False

    def test_list_creators(self, creator_service, mock_db, sample_creator_data):
        """Test listing creators with pagination."""
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_creator_data
        ]

        creators = creator_service.list_creators(skip=0, limit=10)

        assert isinstance(creators, list)
        assert len(creators) == 1

    def test_list_creators_empty(self, creator_service, mock_db):
        """Test listing creators when none exist."""
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

        creators = creator_service.list_creators(skip=0, limit=10)

        assert creators == []

    def test_verify_creator(self, creator_service, mock_db, sample_creator_data):
        """Test verifying a creator."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data
        mock_db.commit.return_value = None

        result = creator_service.verify_creator("creator-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_increment_follower_count(self, creator_service, mock_db, sample_creator_data):
        """Test incrementing follower count."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator_data
        mock_db.commit.return_value = None

        result = creator_service.increment_follower_count("creator-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_search_creators(self, creator_service, mock_db, sample_creator_data):
        """Test searching creators by name or username."""
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_creator_data]

        results = creator_service.search_creators("test")

        assert isinstance(results, list)
        assert len(results) == 1
