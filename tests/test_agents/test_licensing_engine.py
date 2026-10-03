"""Tests for licensing engine agents."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ugc_marketplace.agents.licensing_engine import (
    LicenseStatus,
    LicenseTerms,
    LicenseType,
    UsageType,
    _create_license_impl,
    _LICENSE_STORE,
    create_license,
    get_license_terms,
    validate_license,
)


@pytest.fixture(autouse=True)
def clean_license_store():
    """Clean the license store before and after each test."""
    _LICENSE_STORE.clear()
    yield
    _LICENSE_STORE.clear()


@pytest.fixture
def sample_content_id() -> str:
    """Sample content ID for testing."""
    return "content_001"


@pytest.fixture
def sample_licensee() -> str:
    """Sample licensee ID for testing."""
    return "user_002"


@pytest.fixture
def sample_terms() -> dict:
    """Sample license terms for testing."""
    return {
        "license_type": "commercial",
        "max_usage_count": 100,
        "allowed_usages": ["view", "download"],
        "requires_attribution": True,
    }


@pytest.fixture
def sample_license_terms() -> LicenseTerms:
    """Sample LicenseTerms object for testing."""
    return LicenseTerms(
        license_type=LicenseType.COMMERCIAL,
        max_usage_count=100,
        allowed_usages=[UsageType.VIEW, UsageType.DOWNLOAD],
        requires_attribution=True,
        allows_modification=False,
        allows_redistribution=False,
        valid_until=datetime.now(timezone.utc) + timedelta(days=365),
        royalty_percentage=5.0,
    )


@pytest.fixture
def stored_license(sample_content_id, sample_licensee, sample_license_terms):
    """Create a license in the store using _create_license_impl."""
    return _create_license_impl(
        sample_content_id,
        sample_license_terms,
        licensor_id="creator_001",
        licensee_id=sample_licensee,
    )


# ---------------------------------------------------------------------------
# Tests for create_license
# ---------------------------------------------------------------------------

class TestCreateLicense:
    """Tests for the create_license function."""

    def test_create_license_returns_dict_with_required_fields(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license returns a dict with all required fields."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert isinstance(result, dict)
        assert "license_id" in result
        assert "content_id" in result
        assert "licensee" in result
        assert "terms" in result
        assert "created_at" in result
        assert "status" in result

    def test_create_license_sets_correct_content_id(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license sets the correct content_id."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert result["content_id"] == sample_content_id

    def test_create_license_sets_correct_licensee(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license sets the correct licensee."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert result["licensee"] == sample_licensee

    def test_create_license_preserves_terms(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license preserves the terms dict."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert result["terms"] == sample_terms

    def test_create_license_generates_unique_license_ids(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license generates unique license IDs."""
        result1 = create_license(sample_content_id, sample_licensee, sample_terms)
        result2 = create_license(sample_content_id, sample_licensee, sample_terms)
        assert result1["license_id"] != result2["license_id"]

    def test_create_license_sets_status_active(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license sets status to 'active'."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert result["status"] == "active"

    def test_create_license_includes_created_at_timestamp(self, sample_content_id, sample_licensee, sample_terms):
        """Test that create_license includes a created_at timestamp."""
        result = create_license(sample_content_id, sample_licensee, sample_terms)
        assert "created_at" in result
        assert result["created_at"] is not None

    def test_create_license_raises_on_empty_content_id(self, sample_licensee, sample_terms):
        """Test that create_license raises ValueError on empty content_id."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            create_license("", sample_licensee, sample_terms)

    def test_create_license_raises_on_non_string_content_id(self, sample_licensee, sample_terms):
        """Test that create_license raises ValueError on non-string content_id."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            create_license(123, sample_licensee, sample_terms)

    def test_create_license_raises_on_empty_licensee(self, sample_content_id, sample_terms):
        """Test that create_license raises ValueError on empty licensee."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            create_license(sample_content_id, "", sample_terms)

    def test_create_license_raises_on_non_string_licensee(self, sample_content_id, sample_terms):
        """Test that create_license raises ValueError on non-string licensee."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            create_license(sample_content_id, 123, sample_terms)

    def test_create_license_raises_on_non_dict_terms(self, sample_content_id, sample_licensee):
        """Test that create_license raises ValueError on non-dict terms."""
        with pytest.raises(ValueError, match="terms must be a dictionary"):
            create_license(sample_content_id, sample_licensee, "not_a_dict")

    def test_create_license_with_empty_terms_dict(self, sample_content_id, sample_licensee):
        """Test that create_license works with an empty terms dict."""
        result = create_license(sample_content_id, sample_licensee, {})
        assert result["terms"] == {}
        assert result["status"] == "active"


# ---------------------------------------------------------------------------
# Tests for validate_license
# ---------------------------------------------------------------------------

class TestValidateLicense:
    """Tests for the validate_license function."""

    def test_validate_license_raises_on_empty_license_id(self):
        """Test that validate_license raises ValueError on empty license_id."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            validate_license("")

    def test_validate_license_raises_on_non_string_license_id(self):
        """Test that validate_license raises ValueError on non-string license_id."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            validate_license(123)

    def test_validate_license_returns_not_found_for_unknown_license(self):
        """Test that validate_license returns not_found for unknown license."""
        result = validate_license("LIC-NONEXISTENT")
        assert result["license_id"] == "LIC-NONEXISTENT"
        assert result["is_valid"] is False
        assert result["status"] == "not_found"
        assert "validated_at" in result

    def test_validate_license_returns_valid_for_active_license(self, stored_license):
        """Test that validate_license returns valid for an active license."""
        result = validate_license(stored_license.license_id)
        assert result["license_id"] == stored_license.license_id
        assert result["is_valid"] is True
        assert result["status"] == "active"
        assert "validated_at" in result

    def test_validate_license_returns_invalid_for_revoked_license(self, stored_license):
        """Test that validate_license returns invalid for a revoked license."""
        stored_license.status = LicenseStatus.REVOKED
        result = validate_license(stored_license.license_id)
        assert result["is_valid"] is False
        assert result["status"] == "revoked"

    def test_validate_license_returns_invalid_for_suspended_license(self, stored_license):
        """Test that validate_license returns invalid for a suspended license."""
        stored_license.status = LicenseStatus.SUSPENDED
        result = validate_license(stored_license.license_id)
        assert result["is_valid"] is False
        assert result["status"] == "suspended"

    def test_validate_license_returns_invalid_for_pending_license(self, stored_license):
        """Test that validate_license returns invalid for a pending license."""
        stored_license.status = LicenseStatus.PENDING
        result = validate_license(stored_license.license_id)
        assert result["is_valid"] is False
        assert result["status"] == "pending"

    def test_validate_license_returns_invalid_for_expired_license(self, stored_license):
        """Test that validate_license returns invalid for an expired license."""
        stored_license.status = LicenseStatus.EXPIRED
        result = validate_license(stored_license.license_id)
        assert result["is_valid"] is False
        assert result["status"] == "expired"

    def test_validate_license_includes_validated_at_timestamp(self, stored_license):
        """Test that validate_license includes a validated_at timestamp."""
        result = validate_license(stored_license.license_id)
        assert "validated_at" in result
        assert result["validated_at"] is not None


# ---------------------------------------------------------------------------
# Tests for get_license_terms
# ---------------------------------------------------------------------------

class TestGetLicenseTerms:
    """Tests for the get_license_terms function."""

    def test_get_license_terms_raises_on_empty_license_id(self):
        """Test that get_license_terms raises ValueError on empty license_id."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            get_license_terms("")

    def test_get_license_terms_raises_on_non_string_license_id(self):
        """Test that get_license_terms raises ValueError on non-string license_id."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            get_license_terms(123)

    def test_get_license_terms_returns_empty_terms_for_unknown_license(self):
        """Test that get_license_terms returns empty terms for unknown license."""
        result = get_license_terms("LIC-NONEXISTENT")
        assert result["license_id"] == "LIC-NONEXISTENT"
        assert result["terms"] == {}
        assert "retrieved_at" in result

    def test_get_license_terms_returns_terms_for_stored_license(self, stored_license, sample_license_terms):
        """Test that get_license_terms returns the correct terms for a stored license."""
        result = get_license_terms(stored_license.license_id)
        assert result["license_id"] == stored_license.license_id
        assert result["terms"]["license_type"] == sample_license_terms.license_type.value
        assert result["terms"]["max_usage_count"] == sample_license_terms.max_usage_count
        assert result["terms"]["requires_attribution"] == sample_license_terms.requires_attribution
        assert result["terms"]["allows_modification"] == sample_license_terms.allows_modification
        assert result["terms"]["allows_redistribution"] == sample_license_terms.allows_redistribution
        assert result["terms"]["royalty_percentage"] == sample_license_terms.royalty_percentage
        assert "retrieved_at" in result

    def test_get_license_terms_includes_allowed_usages(self, stored_license, sample_license_terms):
        """Test that get_license_terms includes allowed usages."""
        result = get_license_terms(stored_license.license_id)
        assert "allowed_usages" in result["terms"]
        assert set(result["terms"]["allowed_usages"]) == {u.value for u in sample_license_terms.allowed_usages}

    def test_get_license_terms_includes_validity_period(self, stored_license, sample_license_terms):
        """Test that get_license_terms includes validity period."""
        result = get_license_terms(stored_license.license_id)
        assert "valid_from" in result["terms"]
        assert "valid_until" in result["terms"]
        assert result["terms"]["valid_until"] is not None

    def test_get_license_terms_includes_territory_restrictions(self, stored_license):
        """Test that get_license_terms includes territory restrictions."""
        result = get_license_terms(stored_license.license_id)
        assert "territory_restrictions" in result["terms"]
        assert isinstance(result["terms"]["territory_restrictions"], list)

    def test_get_license_terms_includes_metadata(self, stored_license):
        """Test that get_license_terms includes metadata."""
        result = get_license_terms(stored_license.license_id)
        assert "metadata" in result["terms"]
        assert isinstance(result["terms"]["metadata"], dict)

    def test_get_license_terms_includes_retrieved_at_timestamp(self, stored_license):
        """Test that get_license_terms includes a retrieved_at timestamp."""
        result = get_license_terms(stored_license.license_id)
        assert "retrieved_at" in result
        assert result["retrieved_at"] is not None
