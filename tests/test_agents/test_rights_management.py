"""Tests for rights management module-level functions."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from ugc_marketplace.agents.rights_management import (
    AccessCheckResult,
    AccessDecision,
    GrantResult,
    RightType,
    RightsManagementAgent,
    RightsRecord,
    check_content_rights,
    check_rights,
    grant_rights,
    license_content,
    revoke_license,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_content_id() -> str:
    """Sample content ID for testing."""
    return "content-001"


@pytest.fixture
def sample_user_id() -> str:
    """Sample user ID for testing."""
    return "user-viewer-10"


@pytest.fixture
def sample_licensee() -> str:
    """Sample licensee identifier for testing."""
    return "licensee-corp-001"


@pytest.fixture
def valid_license_terms() -> dict[str, Any]:
    """Valid license terms for testing."""
    return {
        "usage_type": "commercial",
        "duration_days": 365,
        "territory": "worldwide",
        "exclusive": False,
    }


@pytest.fixture
def mock_licenses_db() -> dict[str, dict[str, Any]]:
    """Empty mock licenses database for testing."""
    return {}


# ---------------------------------------------------------------------------
# check_content_rights Tests
# ---------------------------------------------------------------------------


class TestCheckContentRights:
    """Tests for the check_content_rights function."""

    def test_returns_dict_with_required_keys(
        self, sample_content_id: str
    ) -> None:
        """Test that check_content_rights returns a dict with required keys."""
        result = check_content_rights(sample_content_id, "commercial")
        assert isinstance(result, dict)
        assert "content_id" in result
        assert "usage_type" in result
        assert "allowed" in result
        assert "reason" in result
        assert "checked_at" in result

    def test_returns_correct_content_id(
        self, sample_content_id: str
    ) -> None:
        """Test that result contains the correct content_id."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["content_id"] == sample_content_id

    def test_returns_correct_usage_type(
        self, sample_content_id: str
    ) -> None:
        """Test that result contains the correct usage_type."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["usage_type"] == "commercial"

    def test_allowed_for_registered_content(
        self, sample_content_id: str
    ) -> None:
        """Test that registered content is allowed for valid usage types."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["allowed"] is True

    def test_not_allowed_for_unregistered_content(self) -> None:
        """Test that unregistered content is not allowed."""
        result = check_content_rights("nonexistent-content", "commercial")
        assert result["allowed"] is False
        assert "not found" in result["reason"].lower()

    @pytest.mark.parametrize(
        "usage_type",
        ["commercial", "non-commercial", "editorial", "personal"],
    )
    def test_all_valid_usage_types(
        self, sample_content_id: str, usage_type: str
    ) -> None:
        """Test that all valid usage types are accepted."""
        result = check_content_rights(sample_content_id, usage_type)
        assert result["usage_type"] == usage_type
        assert result["allowed"] is True

    def test_empty_content_id_raises_value_error(self) -> None:
        """Test that empty content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            check_content_rights("", "commercial")

    def test_whitespace_content_id_raises_value_error(self) -> None:
        """Test that whitespace-only content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            check_content_rights("   ", "commercial")

    def test_invalid_usage_type_raises_value_error(
        self, sample_content_id: str
    ) -> None:
        """Test that invalid usage_type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported usage_type"):
            check_content_rights(sample_content_id, "invalid_type")

    def test_checked_at_is_iso_format(self, sample_content_id: str) -> None:
        """Test that checked_at is an ISO-8601 formatted string."""
        result = check_content_rights(sample_content_id, "commercial")
        # Should not raise
        datetime.fromisoformat(result["checked_at"])

    def test_reason_is_string(self, sample_content_id: str) -> None:
        """Test that reason is a string."""
        result = check_content_rights(sample_content_id, "commercial")
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# license_content Tests
# ---------------------------------------------------------------------------


class TestLicenseContent:
    """Tests for the license_content function."""

    def test_returns_dict_with_required_keys(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that license_content returns a dict with required keys."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert isinstance(result, dict)
        assert "license_id" in result
        assert "content_id" in result
        assert "licensee" in result
        assert "terms" in result
        assert "status" in result
        assert "created_at" in result

    def test_returns_correct_content_id(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct content_id."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["content_id"] == sample_content_id

    def test_returns_correct_licensee(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct licensee."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["licensee"] == sample_licensee

    def test_returns_correct_terms(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct terms."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["terms"] == valid_license_terms

    def test_status_is_active(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that newly created license has status 'active'."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["status"] == "active"

    def test_license_id_is_uuid(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that license_id is a valid UUID."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        # Should not raise
        uuid.UUID(result["license_id"])

    def test_created_at_is_iso_format(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that created_at is an ISO-8601 formatted string."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        # Should not raise
        datetime.fromisoformat(result["created_at"])

    def test_empty_content_id_raises_value_error(
        self, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that empty content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            license_content("", sample_licensee, valid_license_terms)

    def test_whitespace_content_id_raises_value_error(
        self, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that whitespace-only content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            license_content("   ", sample_licensee, valid_license_terms)

    def test_empty_licensee_raises_value_error(
        self, sample_content_id: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that empty licensee raises ValueError."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            license_content(sample_content_id, "", valid_license_terms)

    def test_whitespace_licensee_raises_value_error(
        self, sample_content_id: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that whitespace-only licensee raises ValueError."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            license_content(sample_content_id, "   ", valid_license_terms)

    def test_non_dict_terms_raises_value_error(
        self, sample_content_id: str, sample_licensee: str
    ) -> None:
        """Test that non-dict terms raises ValueError."""
        with pytest.raises(ValueError, match="terms must be a dictionary"):
            license_content(sample_content_id, sample_licensee, "not a dict")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "missing_key",
        ["usage_type", "duration_days", "territory", "exclusive"],
    )
    def test_missing_required_term_raises_value_error(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        missing_key: str,
    ) -> None:
        """Test that missing required terms raise ValueError."""
        terms = valid_license_terms.copy()
        del terms[missing_key]
        with pytest.raises(ValueError, match="Missing required license terms"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_invalid_usage_type_in_terms_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that invalid usage_type in terms raises ValueError."""
        terms = valid_license_terms.copy()
        terms["usage_type"] = "invalid"
        with pytest.raises(ValueError, match="Invalid usage_type"):
            license_content(sample_content_id, sample_licensee, terms)

    @pytest.mark.parametrize("duration_days", [0, -1, -100])
    def test_non_positive_duration_raises_value_error(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        duration_days: int,
    ) -> None:
        """Test that non-positive duration_days raises ValueError."""
        terms = valid_license_terms.copy()
        terms["duration_days"] = duration_days
        with pytest.raises(ValueError, match="duration_days must be a positive integer"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_non_int_duration_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that non-integer duration_days raises ValueError."""
        terms = valid_license_terms.copy()
        terms["duration_days"] = "365"  # type: ignore[typeddict-item]
        with pytest.raises(ValueError, match="duration_days must be a positive integer"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_non_bool_exclusive_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that non-boolean exclusive raises ValueError."""
        terms = valid_license_terms.copy()
        terms["exclusive"] = "yes"  # type: ignore[typeddict-item]
        with pytest.raises(ValueError, match="exclusive must be a boolean"):
            license_content(sample_content_id, sample_licensee, terms)

    @pytest.mark.parametrize(
        "usage_type",
        ["commercial", "non-commercial", "editorial", "personal"],
    )
    def test_all_valid_usage_types_in_terms(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        usage_type: str,
    ) -> None:
        """Test that all valid usage types are accepted in terms."""
        terms = valid_license_terms.copy()
        terms["usage_type"] = usage_type
        result = license_content(sample_content_id, sample_licensee, terms)
        assert result["terms"]["usage_type"] == usage_type

    def test_terms_are_copied(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that the original terms dict is not modified."""
        original_terms = valid_license_terms.copy()
        license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert valid_license_terms == original_terms


# ---------------------------------------------------------------------------
# revoke_license Tests
# ---------------------------------------------------------------------------


class TestRevokeLicense:
    """Tests for the revoke_license function."""

    def test_returns_true_for_valid_license(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoking a valid license returns True."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        result = revoke_license(license_id)
        assert result is True

    def test_returns_false_for_nonexistent_license(self) -> None:
        """Test that revoking a nonexistent license returns False."""
        result = revoke_license(str(uuid.uuid4()))
        assert result is False

    def test_returns_false_for_already_revoked_license(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoking an already revoked license returns False."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        # First revocation should succeed
        assert revoke_license(license_id) is True
        # Second revocation should fail
        assert revoke_license(license_id) is False

    def test_empty_license_id_raises_value_error(self) -> None:
        """Test that empty license_id raises ValueError."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            revoke_license("")

    def test_whitespace_license_id_raises_value_error(self) -> None:
        """Test that whitespace-only license_id raises ValueError."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            revoke_license("   ")

    def test_revoked_license_has_revoked_status(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoked license has status 'revoked'."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        revoke_license(license_id)
        # Check the internal state
        from ugc_marketplace.agents.rights_management import _MOCK_LICENSES
        assert _MOCK_LICENSES[license_id]["status"] == "revoked"

    def test_revoked_license_has_revoked_at_timestamp(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoked license has a revoked_at timestamp."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        revoke_license(license_id)
        from ugc_marketplace.agents.rights_management import _MOCK_LICENSES
        assert "revoked_at" in _MOCK_LICENSES[license_id]
        # Should be a valid ISO format
        datetime.fromisoformat(_MOCK_LICENSES[license_id]["revoked_at"])


# ---------------------------------------------------------------------------
# RightsManagementAgent Tests
# ---------------------------------------------------------------------------


class TestRightsManagementAgent:
    """Tests for the RightsManagementAgent class."""

    @pytest.fixture
    def agent(self) -> RightsManagementAgent:
        """Create a fresh RightsManagementAgent for each test."""
        return RightsManagementAgent()

    def test_check_rights_owner_has_all_rights(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that content owner has all rights."""
        result = agent.check_rights("content-001", "user-admin-01", RightType.VIEW)
        assert result.decision == AccessDecision.ALLOWED
        assert result.granted_rights == set(RightType)

    def test_check_rights_with_valid_grant(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test check_rights with a valid rights grant."""
        result = agent.check_rights("content-001", "user-viewer-10", RightType.VIEW)
        assert result.decision == AccessDecision.ALLOWED
        assert RightType.VIEW in result.granted_rights

    def test_check_rights_without_grant_denied(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that check_rights denies access without a grant."""
        result = agent.check_rights("content-001", "user-unknown", RightType.VIEW)
        assert result.decision == AccessDecision.DENIED

    def test_check_rights_pending_request(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that pending requests return PENDING decision."""
        result = agent.check_rights("content-005", "user-viewer-10", RightType.VIEW)
        assert result.decision == AccessDecision.PENDING

    def test_check_rights_expired_grant(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that expired grants return EXPIRED decision."""
        # content-002 has an expiry of 2026-10-15 which may be expired
        # depending on current date. Let's create our own expired grant.
        agent.grant_rights(
            "content-001",
            "user-expired",
            {RightType.VIEW},
            duration_days=1,
        )
        # Manually expire it by modifying the record
        key = ("content-001", "user-expired")
        if key in agent._rights_db:
            agent._rights_db[key].expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        result = agent.check_rights("content-001", "user-expired", RightType.VIEW)
        assert result.decision == AccessDecision.EXPIRED

    def test_check_rights_wrong_right_denied(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that having one right doesn't grant another."""
        # user-viewer-10 has VIEW on content-002 but not EDIT
        result = agent.check_rights("content-002", "user-viewer-10", RightType.EDIT)
        assert result.decision == AccessDecision.DENIED

    def test_grant_rights_success(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test successful rights grant."""
        result = agent.grant_rights(
            "content-001",
            "user-new",
            {RightType.VIEW, RightType.DOWNLOAD},
        )
        assert result.success is True
        assert result.content_id == "content-001"
        assert result.user_id == "user-new"
        assert result.rights == {RightType.VIEW, RightType.DOWNLOAD}

    def test_grant_rights_empty_rights_fails(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that granting empty rights set fails."""
        result = agent.grant_rights("content-001", "user-new", set())
        assert result.success is False
        assert "At least one right" in result.message

    def test_grant_rights_with_duration(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test granting rights with a duration."""
        result = agent.grant_rights(
            "content-001",
            "user-temp",
            {RightType.VIEW},
            duration_days=30,
        )
        assert result.success is True
        key = ("content-001", "user-temp")
        assert agent._rights_db[key].expires_at is not None

    def test_grant_rights_invalid_duration_fails(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that invalid duration fails."""
        result = agent.grant_rights(
            "content-001",
            "user-temp",
            {RightType.VIEW},
            duration_days=-1,
        )
        assert result.success is False
        assert "duration_days must be a positive integer" in result.message

    def test_grant_rights_removes_pending(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that granting rights removes pending request."""
        # content-005 has a pending request from user-viewer-10
        agent.grant_rights("content-005", "user-viewer-10", {RightType.VIEW})
        assert ("content-005", "user-viewer-10") not in agent._pending_requests

    def test_revoke_rights_all(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test revoking all rights."""
        agent.grant_rights("content-001", "user-revoke", {RightType.VIEW})
        result = agent.revoke_rights("content-001", "user-revoke")
        assert result is True
        assert ("content-001", "user-revoke") not in agent._rights_db

    def test_revoke_rights_specific(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test revoking specific rights."""
        agent.grant_rights(
            "content-001",
            "user-partial",
            {RightType.VIEW, RightType.DOWNLOAD},
        )
        result = agent.revoke_rights("content-001", "user-partial", {RightType.VIEW})
        assert result is True
        # Should still have DOWNLOAD
        assert agent._rights_db[("content-001", "user-partial")].rights == {RightType.DOWNLOAD}

    def test_revoke_rights_nonexistent_returns_false(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that revoking nonexistent rights returns False."""
        result = agent.revoke_rights("content-001", "user-nonexistent")
        assert result is False

    def test_list_user_rights(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test listing user rights."""
        agent.grant_rights("content-001", "user-list", {RightType.VIEW})
        agent.grant_rights("content-002", "user-list", {RightType.VIEW})
        results = agent.list_user_rights("user-list")
        assert len(results) == 2
        assert all(r.decision == AccessDecision.ALLOWED for r in results)


# ---------------------------------------------------------------------------
# RightsRecord Tests
# ---------------------------------------------------------------------------


class TestRightsRecord:
    """Tests for the RightsRecord dataclass."""

    def test_is_active_no_expiry(self) -> None:
        """Test that record without expiry is always active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        assert record.is_active() is True

    def test_is_active_not_expired(self) -> None:
        """Test that record with future expiry is active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert record.is_active() is True

    def test_is_active_expired(self) -> None:
        """Test that record with past expiry is not active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc) - timedelta(days=10),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert record.is_active() is False


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Tests for RightType and AccessDecision enums."""

    def test_right_type_values(self) -> None:
        """Test that RightType enum has expected values."""
        assert RightType.VIEW == "view"
        assert RightType.DOWNLOAD == "download"
        assert RightType.EDIT == "edit"
        assert RightType.DELETE == "delete"
        assert RightType.SHARE == "share"
        assert RightType.COMMERCIAL_USE == "commercial_use"
        assert RightType.ATTRIBUTION == "attribution"

    def test_access_decision_values(self) -> None:
        """Test that AccessDecision enum has expected values."""
        assert AccessDecision.ALLOWED == "allowed"
        assert AccessDecision.DENIED == "denied"
        assert AccessDecision.PENDING == "pending"
        assert AccessDecision.EXPIRED == "expired"


# ---------------------------------------------------------------------------
# Module-level check_rights and grant_rights Tests
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level check_rights and grant_rights functions."""

    def test_module_level_check_rights(self) -> None:
        """Test module-level check_rights function."""
        result = check_rights("content-001", "user-admin-01", RightType.VIEW)
        assert isinstance(result, AccessCheckResult)
        assert result.decision == AccessDecision.ALLOWED

    def test_module_level_grant_rights(self) -> None:
        """Test module-level grant_rights function."""
        result = grant_rights(
            "content-001",
            "user-module-test",
            {RightType.VIEW},
        )
        assert isinstance(result, GrantResult)
        assert result.success is True
