"""Comprehensive service tests for CreatorService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.ugc_marketplace.models.creator import Creator
from src.ugc_marketplace.services.creator_service import CreatorService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def creator_service(mock_db):
    """Provide a CreatorService instance with a mocked db."""
    return CreatorService(db=mock_db)


@pytest.fixture
def sample_creator():
    """Provide a sample Creator model instance."""
    return Creator(
        id=1,
        username="test_creator",
        email="test@example.com",
        bio="A test creator",
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_creator_dict():
    """Provide a sample creator as a dictionary."""
    return {
        "id": 1,
        "username": "test_creator",
        "email": "test@example.com",
        "bio": "A test creator",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


@pytest.fixture
def multiple_creators():
    """Provide a list of multiple Creator instances."""
    return [
        Creator(
            id=1,
            username="creator_one",
            email="one@example.com",
            bio="First creator",
            is_active=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        Creator(
            id=2,
            username="creator_two",
            email="two@example.com",
            bio="Second creator",
            is_active=False,
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
        Creator(
            id=3,
            username="creator_three",
            email="three@example.com",
            bio="Third creator",
            is_active=True,
            created_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        ),
    ]


# ---------------------------------------------------------------------------
# Tests: get_creator
# ---------------------------------------------------------------------------


class TestGetCreator:
    """Tests for CreatorService.get_creator."""

    def test_get_creator_returns_creator_when_found(
        self, creator_service, mock_db, sample_creator
    ):
        """get_creator returns a Creator when the ID exists."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator

        result = creator_service.get_creator(creator_id=1)

        assert result is not None
        assert result.id == 1
        assert result.username == "test_creator"
        assert result.email == "test@example.com"
        assert result.bio == "A test creator"
        assert result.is_active is True

    def test_get_creator_returns_none_when_not_found(self, creator_service, mock_db):
        """get_creator returns None when the ID does not exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.get_creator(creator_id=999)

        assert result is None

    def test_get_creator_queries_correct_model(self, creator_service, mock_db):
        """get_creator queries the Creator model."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        creator_service.get_creator(creator_id=1)

        mock_db.query.assert_called_once_with(Creator)

    def test_get_creator_with_different_ids(self, creator_service, mock_db):
        """get_creator works with various ID values."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        for cid in [1, 42, 100, 9999]:
            result = creator_service.get_creator(creator_id=cid)
            assert result is None

    def test_get_creator_with_zero_id(self, creator_service, mock_db):
        """get_creator handles zero ID gracefully."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.get_creator(creator_id=0)

        assert result is None

    def test_get_creator_with_negative_id(self, creator_service, mock_db):
        """get_creator handles negative ID gracefully."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.get_creator(creator_id=-1)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: list_creators
# ---------------------------------------------------------------------------


class TestListCreators:
    """Tests for CreatorService.list_creators."""

    def test_list_creators_returns_all_when_no_filters(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators returns all creators when no filters are applied."""
        mock_query = MagicMock()
        mock_query.all.return_value = multiple_creators
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators()

        assert len(result) == 3
        assert result[0].username == "creator_one"
        assert result[1].username == "creator_two"
        assert result[2].username == "creator_three"

    def test_list_creators_with_active_filter(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators filters by is_active=True."""
        active_creators = [c for c in multiple_creators if c.is_active]
        mock_query = MagicMock()
        mock_query.all.return_value = active_creators
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(is_active=True)

        assert len(result) == 2
        assert all(c.is_active for c in result)

    def test_list_creators_with_inactive_filter(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators filters by is_active=False."""
        inactive_creators = [c for c in multiple_creators if not c.is_active]
        mock_query = MagicMock()
        mock_query.all.return_value = inactive_creators
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(is_active=False)

        assert len(result) == 1
        assert result[0].username == "creator_two"
        assert result[0].is_active is False

    def test_list_creators_with_username_filter(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators filters by username substring."""
        mock_query = MagicMock()
        mock_query.all.return_value = [multiple_creators[0]]
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(username="creator_one")

        assert len(result) == 1
        assert result[0].username == "creator_one"

    def test_list_creators_with_email_filter(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators filters by email."""
        mock_query = MagicMock()
        mock_query.all.return_value = [multiple_creators[1]]
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(email="two@example.com")

        assert len(result) == 1
        assert result[0].email == "two@example.com"

    def test_list_creators_with_pagination(self, creator_service, mock_db, multiple_creators):
        """list_creators respects skip and limit parameters."""
        mock_query = MagicMock()
        mock_query.offset.return_value.limit.return_value.all.return_value = multiple_creators[1:3]
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(skip=1, limit=2)

        assert len(result) == 2
        mock_query.offset.assert_called_once_with(1)
        mock_query.offset.return_value.limit.assert_called_once_with(2)

    def test_list_creators_returns_empty_list_when_no_match(self, creator_service, mock_db):
        """list_creators returns empty list when no creators match."""
        mock_query = MagicMock()
        mock_query.all.return_value = []
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(username="nonexistent")

        assert result == []

    def test_list_creators_with_multiple_filters(
        self, creator_service, mock_db, multiple_creators
    ):
        """list_creators applies multiple filters together."""
        mock_query = MagicMock()
        mock_query.all.return_value = [multiple_creators[0]]
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = creator_service.list_creators(is_active=True, username="creator_one")

        assert len(result) == 1
        assert result[0].username == "creator_one"
        assert result[0].is_active is True

    def test_list_creators_default_pagination(self, creator_service, mock_db, multiple_creators):
        """list_creators uses default skip=0 and limit=100."""
        mock_query = MagicMock()
        mock_query.offset.return_value.limit.return_value.all.return_value = multiple_creators
        mock_db.query.return_value = mock_query

        creator_service.list_creators()

        mock_query.offset.assert_called_once_with(0)
        mock_query.offset.return_value.limit.assert_called_once_with(100)


# ---------------------------------------------------------------------------
# Tests: create_creator
# ---------------------------------------------------------------------------


class TestCreateCreator:
    """Tests for CreatorService.create_creator."""

    def test_create_creator_success(self, creator_service, mock_db, sample_creator_dict):
        """create_creator successfully creates a new creator."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 1)

        result = creator_service.create_creator(
            username="new_creator",
            email="new@example.com",
            bio="A new creator",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.username == "new_creator"
        assert result.email == "new@example.com"
        assert result.bio == "A new creator"
        assert result.id == 1

    def test_create_creator_with_minimal_fields(self, creator_service, mock_db):
        """create_creator works with only required fields."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 2)

        result = creator_service.create_creator(
            username="minimal_creator",
            email="minimal@example.com",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.username == "minimal_creator"
        assert result.email == "minimal@example.com"

    def test_create_creator_with_all_fields(self, creator_service, mock_db):
        """create_creator accepts all optional fields."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 3)

        result = creator_service.create_creator(
            username="full_creator",
            email="full@example.com",
            bio="Full bio",
            is_active=False,
        )

        assert result.username == "full_creator"
        assert result.email == "full@example.com"
        assert result.bio == "Full bio"
        assert result.is_active is False

    def test_create_creator_sets_default_is_active(self, creator_service, mock_db):
        """create_creator sets is_active to True by default."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 4)

        result = creator_service.create_creator(
            username="default_active",
            email="default@example.com",
        )

        assert result.is_active is True

    def test_create_creator_commits_to_database(self, creator_service, mock_db):
        """create_creator commits the transaction."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 5)

        creator_service.create_creator(
            username="commit_test",
            email="commit@example.com",
        )

        mock_db.commit.assert_called_once()

    def test_create_creator_refreshes_object(self, creator_service, mock_db):
        """create_creator refreshes the object to get generated fields."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 6)

        result = creator_service.create_creator(
            username="refresh_test",
            email="refresh@example.com",
        )

        mock_db.refresh.assert_called_once()
        assert result.id == 6

    def test_create_creator_raises_on_database_error(self, creator_service, mock_db):
        """create_creator propagates database errors."""
        mock_db.add.return_value = None
        mock_db.commit.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            creator_service.create_creator(
                username="error_creator",
                email="error@example.com",
            )

    def test_create_creator_with_duplicate_username_raises(
        self, creator_service, mock_db
    ):
        """create_creator raises on duplicate username."""
        mock_db.add.return_value = None
        mock_db.commit.side_effect = Exception("Duplicate entry 'duplicate_user'")

        with pytest.raises(Exception, match="Duplicate entry"):
            creator_service.create_creator(
                username="duplicate_user",
                email="dup@example.com",
            )


# ---------------------------------------------------------------------------
# Tests: update_creator
# ---------------------------------------------------------------------------


class TestUpdateCreator:
    """Tests for CreatorService.update_creator."""

    def test_update_creator_success(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator successfully updates a creator."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = creator_service.update_creator(
            creator_id=1,
            username="updated_creator",
            email="updated@example.com",
        )

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.username == "updated_creator"
        assert result.email == "updated@example.com"

    def test_update_creator_partial_update(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator allows partial updates (only some fields)."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = creator_service.update_creator(
            creator_id=1,
            bio="Updated bio only",
        )

        assert result.bio == "Updated bio only"
        assert result.username == "test_creator"
        assert result.email == "test@example.com"

    def test_update_creator_returns_none_when_not_found(self, creator_service, mock_db):
        """update_creator returns None when creator does not exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.update_creator(
            creator_id=999,
            username="nonexistent",
        )

        assert result is None
        mock_db.commit.assert_not_called()

    def test_update_creator_updates_is_active(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator can update the is_active field."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = creator_service.update_creator(
            creator_id=1,
            is_active=False,
        )

        assert result.is_active is False

    def test_update_creator_updates_all_fields(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator can update all fields at once."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = creator_service.update_creator(
            creator_id=1,
            username="completely_updated",
            email="completely@example.com",
            bio="Completely new bio",
            is_active=False,
        )

        assert result.username == "completely_updated"
        assert result.email == "completely@example.com"
        assert result.bio == "Completely new bio"
        assert result.is_active is False

    def test_update_creator_no_changes(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator with no fields still commits (no-op update)."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = creator_service.update_creator(creator_id=1)

        mock_db.commit.assert_called_once()
        assert result.username == "test_creator"

    def test_update_creator_raises_on_database_error(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator propagates database errors."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Update failed"):
            creator_service.update_creator(
                creator_id=1,
                username="fail_update",
            )

    def test_update_creator_queries_correct_id(
        self, creator_service, mock_db, sample_creator
    ):
        """update_creator queries for the correct creator ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        creator_service.update_creator(creator_id=42, username="test")

        mock_db.query.assert_called_once_with(Creator)


# ---------------------------------------------------------------------------
# Tests: delete_creator
# ---------------------------------------------------------------------------


class TestDeleteCreator:
    """Tests for CreatorService.delete_creator."""

    def test_delete_creator_success(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator successfully deletes a creator."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = creator_service.delete_creator(creator_id=1)

        mock_db.delete.assert_called_once_with(sample_creator)
        mock_db.commit.assert_called_once()
        assert result is True

    def test_delete_creator_returns_false_when_not_found(
        self, creator_service, mock_db
    ):
        """delete_creator returns False when creator does not exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = creator_service.delete_creator(creator_id=999)

        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_delete_creator_commits_transaction(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator commits the deletion."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        creator_service.delete_creator(creator_id=1)

        mock_db.commit.assert_called_once()

    def test_delete_creator_deletes_correct_object(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator deletes the correct creator object."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        creator_service.delete_creator(creator_id=1)

        mock_db.delete.assert_called_once_with(sample_creator)

    def test_delete_creator_raises_on_database_error(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator propagates database errors."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.side_effect = Exception("Delete failed")

        with pytest.raises(Exception, match="Delete failed"):
            creator_service.delete_creator(creator_id=1)

    def test_delete_creator_with_different_ids(
        self, creator_service, mock_db, multiple_creators
    ):
        """delete_creator works with various creator IDs."""
        for i, creator in enumerate(multiple_creators):
            mock_db.query.return_value.filter.return_value.first.return_value = creator
            mock_db.delete.return_value = None
            mock_db.commit.return_value = None

            result = creator_service.delete_creator(creator_id=creator.id)

            assert result is True
            mock_db.delete.assert_called_with(creator)

    def test_delete_creator_queries_correct_id(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator queries for the correct creator ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        creator_service.delete_creator(creator_id=42)

        mock_db.query.assert_called_once_with(Creator)

    def test_delete_creator_cascades_or_handles_dependencies(
        self, creator_service, mock_db, sample_creator
    ):
        """delete_creator handles creators with dependencies."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_creator
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = creator_service.delete_creator(creator_id=1)

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
