"""Unit tests for CreatorService.

CreatorService keeps creators in an instance-local dict (``self._creators``)
rather than delegating to a repository, so each test gets a fresh instance and
no storage cleanup is needed between cases.

The service accepts an optional ``db`` argument; it is stored but not used by
the in-memory methods exercised here.
"""
import pytest

from ugc_marketplace.services.creator_service import (
    CreatorNotFoundError,
    CreatorService,
    CreatorValidationError,
)


@pytest.fixture
def service():
    """A fresh CreatorService with its own empty creator store."""
    return CreatorService(db=None)


@pytest.fixture
def valid_data():
    """Minimal valid creator payload."""
    return {"name": "Test Creator", "email": "creator@example.com"}


@pytest.fixture
def existing_creator(service, valid_data):
    """One already-created creator, returned as its stored dict."""
    return service.create_creator(valid_data)


class TestCreateCreator:
    """Tests for CreatorService.create_creator."""

    def test_create_creator_returns_record(self, service, valid_data):
        result = service.create_creator(valid_data)

        assert isinstance(result, dict)
        assert result["name"] == "Test Creator"
        assert result["email"] == "creator@example.com"

    def test_create_creator_generates_id(self, service, valid_data):
        result = service.create_creator(valid_data)

        assert result["id"]
        assert isinstance(result["id"], str)

    def test_created_ids_are_unique(self, service, valid_data):
        first = service.create_creator(valid_data)["id"]
        second = service.create_creator(valid_data)["id"]

        assert first != second

    def test_defaults_are_applied(self, service, valid_data):
        result = service.create_creator(valid_data)

        assert result["bio"] == ""
        assert result["avatar_url"] == ""
        assert result["is_active"] is True
        assert result["metadata"] == {}

    def test_optional_fields_are_persisted(self, service, valid_data):
        valid_data.update({
            "bio": "Loves short-form video",
            "avatar_url": "https://example.com/a.png",
            "is_active": False,
            "metadata": {"tier": "gold"},
        })

        result = service.create_creator(valid_data)

        assert result["bio"] == "Loves short-form video"
        assert result["avatar_url"] == "https://example.com/a.png"
        assert result["is_active"] is False
        assert result["metadata"] == {"tier": "gold"}

    def test_name_and_email_are_trimmed_and_normalised(self, service):
        result = service.create_creator({
            "name": "  Padded Name  ",
            "email": "  Mixed.Case@Example.COM ",
        })

        assert result["name"] == "Padded Name"
        assert result["email"] == "mixed.case@example.com"

    def test_non_dict_raises(self, service):
        with pytest.raises(CreatorValidationError, match="must be a dictionary"):
            service.create_creator("not a dict")

    @pytest.mark.parametrize("name", [None, "", "   ", 123, []])
    def test_invalid_name_raises(self, service, valid_data, name):
        valid_data["name"] = name

        with pytest.raises(CreatorValidationError, match="name is required"):
            service.create_creator(valid_data)

    @pytest.mark.parametrize("email", [None, "", "no-at-sign", 42])
    def test_invalid_email_raises(self, service, valid_data, email):
        valid_data["email"] = email

        with pytest.raises(CreatorValidationError, match="valid email"):
            service.create_creator(valid_data)

    def test_failed_validation_does_not_store_creator(self, service, valid_data):
        valid_data["email"] = "bad"

        with pytest.raises(CreatorValidationError):
            service.create_creator(valid_data)

        assert service.list_creators()["total"] == 0


class TestGetCreator:
    """Tests for CreatorService.get_creator."""

    def test_get_creator(self, service, existing_creator):
        result = service.get_creator(existing_creator["id"])

        assert result["id"] == existing_creator["id"]
        assert result["email"] == existing_creator["email"]

    def test_get_creator_returns_live_reference(self, service, existing_creator):
        """The stored dict is returned directly, not a copy."""
        result = service.get_creator(existing_creator["id"])

        assert result is existing_creator

    def test_get_creator_not_found_raises(self, service):
        with pytest.raises(CreatorNotFoundError, match="not found"):
            service.get_creator("does-not-exist")

    @pytest.mark.parametrize("bad_id", ["", None, 0])
    def test_get_creator_invalid_id_raises(self, service, bad_id):
        with pytest.raises(CreatorValidationError, match="valid creator ID"):
            service.get_creator(bad_id)


class TestListCreators:
    """Tests for CreatorService.list_creators."""

    @pytest.fixture
    def three_creators(self, service):
        """Three creators with distinct names, emails and active flags."""
        return [
            service.create_creator({
                "name": "Alpha One",
                "email": "alpha@example.com",
                "is_active": True,
            }),
            service.create_creator({
                "name": "Beta Two",
                "email": "beta@example.com",
                "is_active": False,
            }),
            service.create_creator({
                "name": "Alpha Three",
                "email": "three@alpha.com",
                "is_active": True,
            }),
        ]

    def test_empty_list_shape(self, service):
        result = service.list_creators()

        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["per_page"] == 20

    def test_lists_all_creators(self, service, three_creators):
        result = service.list_creators()

        assert result["total"] == 3
        assert len(result["items"]) == 3

    def test_filter_by_is_active(self, service, three_creators):
        result = service.list_creators(filters={"is_active": True})

        assert result["total"] == 2
        assert all(c["is_active"] is True for c in result["items"])

    def test_filter_by_name_is_case_insensitive_substring(self, service, three_creators):
        result = service.list_creators(filters={"name": "alpha"})

        assert result["total"] == 2
        assert {c["name"] for c in result["items"]} == {"Alpha One", "Alpha Three"}

    def test_filter_by_email_is_case_insensitive_substring(self, service, three_creators):
        result = service.list_creators(filters={"email": "ALPHA"})

        assert result["total"] == 2

    def test_combined_filters(self, service, three_creators):
        result = service.list_creators(filters={"is_active": True, "name": "alpha"})

        assert result["total"] == 2
        result = service.list_creators(filters={"is_active": False, "name": "alpha"})
        assert result["total"] == 0

    def test_filter_with_no_match(self, service, three_creators):
        result = service.list_creators(filters={"name": "nonexistent"})

        assert result["total"] == 0
        assert result["items"] == []

    def test_pagination_slices_items(self, service, three_creators):
        page1 = service.list_creators(pagination={"page": 1, "per_page": 2})
        page2 = service.list_creators(pagination={"page": 2, "per_page": 2})

        assert len(page1["items"]) == 2
        assert len(page2["items"]) == 1
        # total reflects the filtered set, not the page size
        assert page1["total"] == page2["total"] == 3
        assert {c["id"] for c in page1["items"]}.isdisjoint(
            {c["id"] for c in page2["items"]}
        )

    def test_pagination_page_beyond_range(self, service, three_creators):
        result = service.list_creators(pagination={"page": 99, "per_page": 10})

        assert result["items"] == []
        assert result["total"] == 3

    def test_pagination_page_is_floored_to_one(self, service, three_creators):
        result = service.list_creators(pagination={"page": 0})

        assert result["page"] == 1
        assert len(result["items"]) == 3

    def test_per_page_is_capped_at_100(self, service):
        result = service.list_creators(pagination={"per_page": 5000})

        assert result["per_page"] == 100

    def test_per_page_is_floored_at_one(self, service, three_creators):
        result = service.list_creators(pagination={"per_page": 0})

        assert result["per_page"] == 1
        assert len(result["items"]) == 1


class TestUpdateCreator:
    """Tests for CreatorService.update_creator."""

    def test_update_single_field(self, service, existing_creator):
        result = service.update_creator(existing_creator["id"], {"bio": "New bio"})

        assert result["bio"] == "New bio"
        assert result["name"] == existing_creator["name"]

    def test_update_multiple_fields(self, service, existing_creator):
        result = service.update_creator(
            existing_creator["id"],
            {"name": "Renamed", "is_active": False},
        )

        assert result["name"] == "Renamed"
        assert result["is_active"] is False

    def test_update_is_persisted(self, service, existing_creator):
        service.update_creator(existing_creator["id"], {"bio": "Persisted"})

        assert service.get_creator(existing_creator["id"])["bio"] == "Persisted"

    def test_unknown_fields_are_ignored(self, service, existing_creator):
        result = service.update_creator(
            existing_creator["id"], {"id": "hijacked", "role": "admin"}
        )

        assert result["id"] == existing_creator["id"]
        assert "role" not in result

    def test_update_non_dict_raises(self, service, existing_creator):
        with pytest.raises(CreatorValidationError, match="must be a dictionary"):
            service.update_creator(existing_creator["id"], "nope")

    @pytest.mark.parametrize("bad_id", ["", None])
    def test_update_invalid_id_raises(self, service, bad_id):
        with pytest.raises(CreatorValidationError, match="valid creator ID"):
            service.update_creator(bad_id, {"bio": "x"})

    def test_update_missing_creator_raises(self, service):
        with pytest.raises(CreatorNotFoundError):
            service.update_creator("does-not-exist", {"bio": "x"})

    @pytest.mark.parametrize("name", ["", "   ", None])
    def test_update_to_invalid_name_raises(self, service, existing_creator, name):
        with pytest.raises(CreatorValidationError, match="non-empty string"):
            service.update_creator(existing_creator["id"], {"name": name})

    def test_update_to_invalid_email_raises(self, service, existing_creator):
        with pytest.raises(CreatorValidationError, match="valid email"):
            service.update_creator(existing_creator["id"], {"email": "not-an-email"})

    def test_invalid_update_is_not_atomic(self, service, existing_creator):
        """Documents a known wart: update_creator applies fields in-place.

        Fields are validated and written inside the same loop, so when a later
        field fails validation the earlier ones have already been mutated in
        the stored dict. Here 'name' is applied before the bad 'email' raises.

        Pinning the behaviour so a future atomicity fix shows up as a
        deliberate change rather than a silent surprise.
        """
        creator_id = existing_creator["id"]

        with pytest.raises(CreatorValidationError):
            service.update_creator(creator_id, {"name": "Valid", "email": "bad"})

        stored = service.get_creator(creator_id)
        assert stored["name"] == "Valid"
        assert stored["email"] == existing_creator["email"]

    def test_invalid_email_alone_leaves_record_untouched(self, service, existing_creator):
        """When the bad field is the only change, nothing is mutated."""
        creator_id = existing_creator["id"]

        with pytest.raises(CreatorValidationError):
            service.update_creator(creator_id, {"email": "bad"})

        assert service.get_creator(creator_id)["email"] == existing_creator["email"]


class TestDeleteCreator:
    """Tests for CreatorService.delete_creator."""

    def test_delete_removes_creator(self, service, existing_creator):
        creator_id = existing_creator["id"]

        assert service.delete_creator(creator_id) is True
        with pytest.raises(CreatorNotFoundError):
            service.get_creator(creator_id)

    def test_delete_removes_from_listings(self, service, existing_creator):
        service.delete_creator(existing_creator["id"])

        assert service.list_creators()["total"] == 0

    def test_delete_missing_raises(self, service):
        with pytest.raises(CreatorNotFoundError):
            service.delete_creator("does-not-exist")

    def test_delete_twice_raises(self, service, existing_creator):
        service.delete_creator(existing_creator["id"])

        with pytest.raises(CreatorNotFoundError):
            service.delete_creator(existing_creator["id"])

    @pytest.mark.parametrize("bad_id", ["", None])
    def test_delete_invalid_id_raises(self, service, bad_id):
        with pytest.raises(CreatorValidationError, match="valid creator ID"):
            service.delete_creator(bad_id)


class TestServiceIsolation:
    """Each CreatorService instance owns an independent store."""

    def test_stores_are_not_shared_between_instances(self, valid_data):
        first = CreatorService(db=None)
        second = CreatorService(db=None)

        first.create_creator(valid_data)

        assert second.list_creators()["total"] == 0

    def test_db_argument_is_optional(self):
        assert CreatorService().list_creators()["total"] == 0

    def test_db_argument_is_retained(self):
        sentinel = object()
        assert CreatorService(db=sentinel)._db is sentinel

    @pytest.mark.parametrize(
        "exc_cls",
        [CreatorNotFoundError, CreatorValidationError],
    )
    def test_error_types_are_exceptions(self, exc_cls):
        assert issubclass(exc_cls, Exception)