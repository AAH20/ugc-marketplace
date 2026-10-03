"""Integration tests for content workflow: lifecycle, moderation, and licensing."""
from __future__ import annotations

import pytest

from ugc_marketplace.services.content_service import (
    ContentNotFoundError,
    ContentStatus,
    ContentType,
    create_content,
    delete_content,
    get_content,
    update_content,
)
from ugc_marketplace.agents.content_moderation import (
    ModerationStatus,
    flag_content,
    get_moderation_status,
    moderate_content,
)
from ugc_marketplace.agents.licensing_engine import (
    LicenseStatus,
    LicenseTerms,
    UsageType,
    _create_license_impl,
    _LICENSE_STORE,
    _validate_license_impl,
    create_license,
    revoke_license,
    validate_license,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_content_data() -> dict:
    """Return valid content creation payload."""
    return {
        "title": "Integration Test Content",
        "description": "Content created during integration testing.",
        "content_type": "text",
        "creator_id": "creator_integration_001",
        "tags": ["integration", "test"],
        "metadata": {"source": "integration_test"},
    }


@pytest.fixture
def created_content(sample_content_data):
    """Create a content item and return it."""
    return create_content(sample_content_data)


@pytest.fixture
def licensed_content(created_content):
    """Create content and license it, returning (content, license_dict)."""
    content = created_content
    license_dict = create_license(
        content_id=content.id,
        licensee="licensee_integration_001",
        terms={
            "usage_type": "commercial",
            "duration_days": 365,
            "territory": "worldwide",
            "exclusive": False,
        },
    )
    return content, license_dict


# ---------------------------------------------------------------------------
# Test 1: Full Content Lifecycle (create → update → delete)
# ---------------------------------------------------------------------------


class TestFullContentLifecycle:
    """Integration test: create content → update → delete."""

    def test_create_content(self, sample_content_data):
        """Step 1: Create content and verify initial state."""
        content = create_content(sample_content_data)

        assert content.id is not None
        assert content.title == sample_content_data["title"]
        assert content.description == sample_content_data["description"]
        assert content.content_type == ContentType.TEXT
        assert content.status == ContentStatus.DRAFT
        assert content.creator_id == sample_content_data["creator_id"]
        assert content.tags == sample_content_data["tags"]
        assert content.metadata == sample_content_data["metadata"]
        assert content.created_at is not None
        assert content.updated_at is not None

    def test_update_content(self, created_content):
        """Step 2: Update content and verify changes."""
        content = created_content
        original_updated_at = content.updated_at

        updated = update_content(
            content.id,
            {
                "title": "Updated Integration Title",
                "description": "Updated description for integration test.",
                "status": "published",
                "tags": ["integration", "updated"],
            },
        )

        assert updated.title == "Updated Integration Title"
        assert updated.description == "Updated description for integration test."
        assert updated.status == ContentStatus.PUBLISHED
        assert updated.tags == ["integration", "updated"]
        assert updated.updated_at >= original_updated_at

        # Verify persistence by re-fetching
        fetched = get_content(content.id)
        assert fetched.title == "Updated Integration Title"
        assert fetched.status == ContentStatus.PUBLISHED

    def test_delete_content(self, created_content):
        """Step 3: Delete content and verify removal."""
        content = created_content
        content_id = content.id

        result = delete_content(content_id)
        assert result is True

        # Verify content no longer exists
        with pytest.raises(ContentNotFoundError):
            get_content(content_id)

    def test_full_lifecycle(self, sample_content_data):
        """End-to-end: create → update → delete in sequence."""
        # Create
        content = create_content(sample_content_data)
        content_id = content.id
        assert content.status == ContentStatus.DRAFT

        # Update
        updated = update_content(
            content_id,
            {"title": "Lifecycle Test Updated", "status": "published"},
        )
        assert updated.title == "Lifecycle Test Updated"
        assert updated.status == ContentStatus.PUBLISHED

        # Delete
        assert delete_content(content_id) is True
        with pytest.raises(ContentNotFoundError):
            get_content(content_id)


# ---------------------------------------------------------------------------
# Test 2: Content Moderation Flow (create → moderate → flag)
# ---------------------------------------------------------------------------


class TestContentModerationFlow:
    """Integration test: create content → moderate → flag."""

    def test_moderate_clean_content(self, created_content):
        """Step 1: Moderate content with no violations."""
        content = created_content
        result = moderate_content(content.description)

        assert result["content"] == content.description
        assert result["approved"] is True
        assert result["violations"] == []
        assert result["flagged"] is False

    def test_moderate_violating_content(self):
        """Step 1b: Moderate content that contains violations."""
        violating_text = "Buy cheap products now! Click here for free money!"
        result = moderate_content(violating_text)

        assert result["content"] == violating_text
        assert result["approved"] is False
        assert len(result["violations"]) > 0
        assert result["flagged"] is True

    def test_flag_content(self, created_content):
        """Step 2: Flag content for review."""
        content = created_content
        result = flag_content(content.id, "Reported by user for review")

        assert result is True

        status = get_moderation_status(content.id)
        assert status["content_id"] == content.id
        assert status["status"] == "pending_review"
        assert status["reason"] == "Reported by user for review"

    def test_flag_already_flagged_content(self, created_content):
        """Step 2b: Flagging already-flagged content returns False."""
        content = created_content

        first = flag_content(content.id, "First report")
        assert first is True

        second = flag_content(content.id, "Second report")
        assert second is False

    def test_full_moderation_flow(self, sample_content_data):
        """End-to-end: create → moderate → flag in sequence."""
        # Create
        content = create_content(sample_content_data)
        assert content.status == ContentStatus.DRAFT

        # Moderate (clean content should pass)
        mod_result = moderate_content(content.description)
        assert mod_result["approved"] is True
        assert mod_result["flagged"] is False

        # Flag for review
        flag_result = flag_content(content.id, "Automated flag after moderation")
        assert flag_result is True

        # Verify moderation status
        status = get_moderation_status(content.id)
        assert status["status"] == "pending_review"
        assert status["reason"] == "Automated flag after moderation"


# ---------------------------------------------------------------------------
# Test 3: Content Licensing Flow (create → license → revoke)
# ---------------------------------------------------------------------------


class TestContentLicensingFlow:
    """Integration test: create content → license → revoke."""

    def test_license_content(self, created_content):
        """Step 1: License content to a licensee."""
        content = created_content
        license_dict = create_license(
            content_id=content.id,
            licensee="licensee_integration_001",
            terms={
                "usage_type": "commercial",
                "duration_days": 365,
                "territory": "worldwide",
                "exclusive": False,
            },
        )

        assert license_dict["license_id"] is not None
        assert license_dict["content_id"] == content.id
        assert license_dict["licensee"] == "licensee_integration_001"
        assert license_dict["status"] == "active"
        assert license_dict["terms"]["usage_type"] == "commercial"
        assert license_dict["created_at"] is not None

    def test_validate_active_license(self, licensed_content):
        """Step 2: Validate the active license."""
        content, license_dict = licensed_content

        validation = validate_license(license_dict["license_id"])
        assert validation["is_valid"] is True
        assert validation["status"] == "active"

    def test_revoke_license(self, licensed_content):
        """Step 3: Revoke the license and verify."""
        content, license_dict = licensed_content

        result = revoke_license(license_dict["license_id"])
        assert result is True

        # Validate after revocation
        validation = validate_license(license_dict["license_id"])
        assert validation["is_valid"] is False
        assert validation["status"] == "revoked"

    def test_revoke_nonexistent_license(self):
        """Step 3b: Revoking a non-existent license returns False."""
        result = revoke_license("non-existent-license-id")
        assert result is False

    def test_full_licensing_flow(self, sample_content_data):
        """End-to-end: create → license → validate → revoke in sequence."""
        # Create
        content = create_content(sample_content_data)
        assert content.status == ContentStatus.DRAFT

        # License
        license_dict = create_license(
            content_id=content.id,
            licensee="licensee_e2e_001",
            terms={
                "usage_type": "non-commercial",
                "duration_days": 30,
                "territory": "US",
                "exclusive": False,
            },
        )
        assert license_dict["status"] == "active"

        # Validate while active
        validation = validate_license(license_dict["license_id"])
        assert validation["is_valid"] is True
        assert validation["status"] == "active"

        # Revoke
        assert revoke_license(license_dict["license_id"]) is True

        # Validate after revocation
        validation = validate_license(license_dict["license_id"])
        assert validation["is_valid"] is False
        assert validation["status"] == "revoked"
