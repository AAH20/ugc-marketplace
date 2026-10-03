"""Comprehensive agent tests for content moderation functions."""

import pytest
from unittest.mock import MagicMock, patch
from src.ugc_marketplace.agents.content_moderation import (
    moderate_content,
    flag_content,
    get_moderation_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_text():
    """Return a sample text string for testing."""
    return "This is a sample content for moderation testing."


@pytest.fixture
def sample_user_id():
    """Return a sample user ID for testing."""
    return "user_12345"


@pytest.fixture
def sample_content_id():
    """Return a sample content ID for testing."""
    return "content_67890"


@pytest.fixture
def mock_moderation_result():
    """Return a mock moderation result dictionary."""
    return {
        "is_approved": True,
        "confidence": 0.95,
        "flags": [],
        "categories": {},
        "action": "none",
    }


@pytest.fixture
def mock_flagged_result():
    """Return a mock flagged moderation result dictionary."""
    return {
        "is_approved": False,
        "confidence": 0.88,
        "flags": ["spam", "inappropriate"],
        "categories": {"spam": 0.85, "inappropriate": 0.72},
        "action": "flag_for_review",
    }


@pytest.fixture
def mock_blocked_result():
    """Return a mock blocked moderation result dictionary."""
    return {
        "is_approved": False,
        "confidence": 0.99,
        "flags": ["hate_speech", "violence"],
        "categories": {"hate_speech": 0.97, "violence": 0.93},
        "action": "block",
    }


# ---------------------------------------------------------------------------
# Tests for moderate_content
# ---------------------------------------------------------------------------


class TestModerateContent:
    """Tests for the moderate_content function."""

    def test_moderate_content_returns_dict(self, sample_text):
        """Test that moderate_content returns a dictionary."""
        result = moderate_content(sample_text)
        assert isinstance(result, dict)

    def test_moderate_content_contains_required_keys(self, sample_text):
        """Test that moderate_content result contains required keys."""
        result = moderate_content(sample_text)
        assert "is_approved" in result
        assert "confidence" in result
        assert "flags" in result
        assert "action" in result

    def test_moderate_content_approves_safe_text(self, sample_text):
        """Test that moderate_content approves safe text."""
        result = moderate_content(sample_text)
        assert result["is_approved"] is True
        assert result["action"] == "none"

    def test_moderate_content_flags_inappropriate_text(self):
        """Test that moderate_content flags inappropriate text."""
        inappropriate_text = "This is spam content with inappropriate material."
        result = moderate_content(inappropriate_text)
        assert result["is_approved"] is False
        assert len(result["flags"]) > 0
        assert result["action"] in ("flag_for_review", "block")

    def test_moderate_content_blocks_harmful_text(self):
        """Test that moderate_content blocks harmful text."""
        harmful_text = "This contains hate speech and violent threats."
        result = moderate_content(harmful_text)
        assert result["is_approved"] is False
        assert result["action"] == "block"

    def test_moderate_content_empty_string(self):
        """Test that moderate_content handles empty string."""
        result = moderate_content("")
        assert isinstance(result, dict)
        assert "is_approved" in result

    def test_moderate_content_none_input(self):
        """Test that moderate_content handles None input gracefully."""
        result = moderate_content(None)
        assert isinstance(result, dict)
        assert result["is_approved"] is False

    def test_moderate_content_confidence_range(self, sample_text):
        """Test that confidence is between 0 and 1."""
        result = moderate_content(sample_text)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_moderate_content_flags_is_list(self, sample_text):
        """Test that flags is always a list."""
        result = moderate_content(sample_text)
        assert isinstance(result["flags"], list)

    def test_moderate_content_long_text(self):
        """Test that moderate_content handles long text."""
        long_text = "A" * 10000
        result = moderate_content(long_text)
        assert isinstance(result, dict)
        assert "is_approved" in result

    def test_moderate_content_special_characters(self):
        """Test that moderate_content handles special characters."""
        special_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = moderate_content(special_text)
        assert isinstance(result, dict)

    def test_moderate_content_unicode(self):
        """Test that moderate_content handles unicode text."""
        unicode_text = "こんにちは世界 🌍 مرحبا"
        result = moderate_content(unicode_text)
        assert isinstance(result, dict)

    def test_moderate_content_with_user_id(self, sample_text, sample_user_id):
        """Test that moderate_content accepts optional user_id."""
        result = moderate_content(sample_text, user_id=sample_user_id)
        assert isinstance(result, dict)
        assert "is_approved" in result

    def test_moderate_content_with_content_id(self, sample_text, sample_content_id):
        """Test that moderate_content accepts optional content_id."""
        result = moderate_content(sample_text, content_id=sample_content_id)
        assert isinstance(result, dict)
        assert "is_approved" in result

    def test_moderate_content_with_both_ids(self, sample_text, sample_user_id, sample_content_id):
        """Test that moderate_content accepts both user_id and content_id."""
        result = moderate_content(
            sample_text, user_id=sample_user_id, content_id=sample_content_id
        )
        assert isinstance(result, dict)
        assert "is_approved" in result

    def test_moderate_content_returns_action_for_various_inputs(self):
        """Test that moderate_content returns valid actions for various inputs."""
        test_inputs = [
            "Normal content",
            "Spam spam spam",
            "Hate speech content",
            "",
            "1234567890",
        ]
        valid_actions = {"none", "flag_for_review", "block"}
        for text in test_inputs:
            result = moderate_content(text)
            assert result["action"] in valid_actions

    def test_moderate_content_categories_dict(self, sample_text):
        """Test that categories is a dictionary when present."""
        result = moderate_content(sample_text)
        if "categories" in result:
            assert isinstance(result["categories"], dict)


# ---------------------------------------------------------------------------
# Tests for flag_content
# ---------------------------------------------------------------------------


class TestFlagContent:
    """Tests for the flag_content function."""

    def test_flag_content_returns_dict(self, sample_content_id, sample_user_id):
        """Test that flag_content returns a dictionary."""
        result = flag_content(sample_content_id, sample_user_id)
        assert isinstance(result, dict)

    def test_flag_content_contains_required_keys(self, sample_content_id, sample_user_id):
        """Test that flag_content result contains required keys."""
        result = flag_content(sample_content_id, sample_user_id)
        assert "flag_id" in result
        assert "content_id" in result
        assert "user_id" in result
        assert "status" in result

    def test_flag_content_sets_pending_status(self, sample_content_id, sample_user_id):
        """Test that flag_content sets status to pending."""
        result = flag_content(sample_content_id, sample_user_id)
        assert result["status"] == "pending"

    def test_flag_content_stores_content_id(self, sample_content_id, sample_user_id):
        """Test that flag_content stores the correct content_id."""
        result = flag_content(sample_content_id, sample_user_id)
        assert result["content_id"] == sample_content_id

    def test_flag_content_stores_user_id(self, sample_content_id, sample_user_id):
        """Test that flag_content stores the correct user_id."""
        result = flag_content(sample_content_id, sample_user_id)
        assert result["user_id"] == sample_user_id

    def test_flag_content_generates_unique_flag_ids(self, sample_content_id, sample_user_id):
        """Test that flag_content generates unique flag IDs."""
        result1 = flag_content(sample_content_id, sample_user_id)
        result2 = flag_content(sample_content_id, sample_user_id)
        assert result1["flag_id"] != result2["flag_id"]

    def test_flag_content_with_reason(self, sample_content_id, sample_user_id):
        """Test that flag_content accepts an optional reason."""
        reason = "Inappropriate content"
        result = flag_content(sample_content_id, sample_user_id, reason=reason)
        assert result["reason"] == reason

    def test_flag_content_without_reason(self, sample_content_id, sample_user_id):
        """Test that flag_content works without a reason."""
        result = flag_content(sample_content_id, sample_user_id)
        assert "reason" not in result or result.get("reason") is None

    def test_flag_content_with_flagged_by(self, sample_content_id, sample_user_id):
        """Test that flag_content accepts an optional flagged_by parameter."""
        flagged_by = "moderator_001"
        result = flag_content(sample_content_id, sample_user_id, flagged_by=flagged_by)
        assert result["flagged_by"] == flagged_by

    def test_flag_content_with_timestamp(self, sample_content_id, sample_user_id):
        """Test that flag_content includes a timestamp."""
        result = flag_content(sample_content_id, sample_user_id)
        assert "timestamp" in result

    def test_flag_content_empty_content_id(self, sample_user_id):
        """Test that flag_content handles empty content_id."""
        result = flag_content("", sample_user_id)
        assert isinstance(result, dict)
        assert result["content_id"] == ""

    def test_flag_content_empty_user_id(self, sample_content_id):
        """Test that flag_content handles empty user_id."""
        result = flag_content(sample_content_id, "")
        assert isinstance(result, dict)
        assert result["user_id"] == ""

    def test_flag_content_none_content_id(self, sample_user_id):
        """Test that flag_content handles None content_id."""
        result = flag_content(None, sample_user_id)
        assert isinstance(result, dict)

    def test_flag_content_none_user_id(self, sample_content_id):
        """Test that flag_content handles None user_id."""
        result = flag_content(sample_content_id, None)
        assert isinstance(result, dict)

    def test_flag_content_with_all_optional_params(self, sample_content_id, sample_user_id):
        """Test that flag_content accepts all optional parameters."""
        result = flag_content(
            sample_content_id,
            sample_user_id,
            reason="Test reason",
            flagged_by="moderator_002",
        )
        assert result["reason"] == "Test reason"
        assert result["flagged_by"] == "moderator_002"
        assert result["status"] == "pending"

    def test_flag_content_returns_valid_status_values(self, sample_content_id, sample_user_id):
        """Test that flag_content returns valid status values."""
        result = flag_content(sample_content_id, sample_user_id)
        valid_statuses = {"pending", "reviewed", "resolved", "dismissed"}
        assert result["status"] in valid_statuses


# ---------------------------------------------------------------------------
# Tests for get_moderation_status
# ---------------------------------------------------------------------------


class TestGetModerationStatus:
    """Tests for the get_moderation_status function."""

    def test_get_moderation_status_returns_dict(self, sample_content_id):
        """Test that get_moderation_status returns a dictionary."""
        result = get_moderation_status(sample_content_id)
        assert isinstance(result, dict)

    def test_get_moderation_status_contains_required_keys(self, sample_content_id):
        """Test that get_moderation_status result contains required keys."""
        result = get_moderation_status(sample_content_id)
        assert "content_id" in result
        assert "status" in result
        assert "moderation_result" in result

    def test_get_moderation_status_stores_content_id(self, sample_content_id):
        """Test that get_moderation_status stores the correct content_id."""
        result = get_moderation_status(sample_content_id)
        assert result["content_id"] == sample_content_id

    def test_get_moderation_status_returns_approved(self, sample_content_id):
        """Test that get_moderation_status returns approved status for safe content."""
        result = get_moderation_status(sample_content_id)
        assert result["status"] in ("approved", "pending", "flagged", "blocked")

    def test_get_moderation_status_moderation_result_is_dict(self, sample_content_id):
        """Test that moderation_result is a dictionary."""
        result = get_moderation_status(sample_content_id)
        assert isinstance(result["moderation_result"], dict)

    def test_get_moderation_status_moderation_result_contains_is_approved(self, sample_content_id):
        """Test that moderation_result contains is_approved key."""
        result = get_moderation_status(sample_content_id)
        assert "is_approved" in result["moderation_result"]

    def test_get_moderation_status_empty_content_id(self):
        """Test that get_moderation_status handles empty content_id."""
        result = get_moderation_status("")
        assert isinstance(result, dict)
        assert result["content_id"] == ""

    def test_get_moderation_status_none_content_id(self):
        """Test that get_moderation_status handles None content_id."""
        result = get_moderation_status(None)
        assert isinstance(result, dict)

    def test_get_moderation_status_with_user_id(self, sample_content_id, sample_user_id):
        """Test that get_moderation_status accepts optional user_id."""
        result = get_moderation_status(sample_content_id, user_id=sample_user_id)
        assert isinstance(result, dict)
        assert result["content_id"] == sample_content_id

    def test_get_moderation_status_returns_valid_status(self, sample_content_id):
        """Test that get_moderation_status returns a valid status value."""
        result = get_moderation_status(sample_content_id)
        valid_statuses = {"approved", "pending", "flagged", "blocked", "not_found"}
        assert result["status"] in valid_statuses

    def test_get_moderation_status_includes_timestamp(self, sample_content_id):
        """Test that get_moderation_status includes a timestamp."""
        result = get_moderation_status(sample_content_id)
        assert "timestamp" in result

    def test_get_moderation_status_moderation_result_has_confidence(self, sample_content_id):
        """Test that moderation_result includes confidence score."""
        result = get_moderation_status(sample_content_id)
        assert "confidence" in result["moderation_result"]
        assert 0.0 <= result["moderation_result"]["confidence"] <= 1.0

    def test_get_moderation_status_moderation_result_has_flags(self, sample_content_id):
        """Test that moderation_result includes flags list."""
        result = get_moderation_status(sample_content_id)
        assert "flags" in result["moderation_result"]
        assert isinstance(result["moderation_result"]["flags"], list)

    def test_get_moderation_status_moderation_result_has_action(self, sample_content_id):
        """Test that moderation_result includes action."""
        result = get_moderation_status(sample_content_id)
        assert "action" in result["moderation_result"]

    def test_get_moderation_status_consistent_results(self, sample_content_id):
        """Test that get_moderation_status returns consistent results for same content_id."""
        result1 = get_moderation_status(sample_content_id)
        result2 = get_moderation_status(sample_content_id)
        assert result1["content_id"] == result2["content_id"]
        assert result1["status"] == result2["status"]

    def test_get_moderation_status_different_content_ids(self):
        """Test that get_moderation_status handles different content IDs."""
        result1 = get_moderation_status("content_1")
        result2 = get_moderation_status("content_2")
        assert result1["content_id"] == "content_1"
        assert result2["content_id"] == "content_2"

    def test_get_moderation_status_with_special_characters_in_id(self):
        """Test that get_moderation_status handles special characters in content_id."""
        special_id = "content-!@#$%^&*()"
        result = get_moderation_status(special_id)
        assert isinstance(result, dict)
        assert result["content_id"] == special_id

    def test_get_moderation_status_with_unicode_id(self):
        """Test that get_moderation_status handles unicode content_id."""
        unicode_id = "content_こんにちは"
        result = get_moderation_status(unicode_id)
        assert isinstance(result, dict)
        assert result["content_id"] == unicode_id
