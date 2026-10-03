"""Comprehensive agent tests for quality scoring functions.

Tests cover:
- score_content_quality
- get_quality_metrics
- flag_low_quality
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

from src.ugc_marketplace.agents.quality_scoring import (
    score_content_quality,
    get_quality_metrics,
    flag_low_quality,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_content() -> str:
    """Return a sample content string for testing."""
    return (
        "This is a high-quality piece of content that provides "
        "substantial value to the reader with detailed analysis."
    )


@pytest.fixture
def low_quality_content() -> str:
    """Return a low-quality content string for testing."""
    return "bad"


@pytest.fixture
def empty_content() -> str:
    """Return an empty content string for testing."""
    return ""


@pytest.fixture
def mock_quality_response() -> Dict[str, Any]:
    """Return a mock quality scoring API response."""
    return {
        "score": 0.85,
        "metrics": {
            "readability": 0.90,
            "engagement": 0.80,
            "originality": 0.85,
            "depth": 0.82,
        },
        "flags": [],
    }


@pytest.fixture
def mock_low_quality_response() -> Dict[str, Any]:
    """Return a mock low-quality scoring API response."""
    return {
        "score": 0.25,
        "metrics": {
            "readability": 0.30,
            "engagement": 0.20,
            "originality": 0.25,
            "depth": 0.15,
        },
        "flags": ["too_short", "low_engagement"],
    }


@pytest.fixture
def mock_agent_config() -> Dict[str, Any]:
    """Return a mock agent configuration."""
    return {
        "model": "gpt-4",
        "temperature": 0.3,
        "max_tokens": 1024,
        "quality_threshold": 0.6,
    }


# ---------------------------------------------------------------------------
# Tests for score_content_quality
# ---------------------------------------------------------------------------


class TestScoreContentQuality:
    """Tests for the score_content_quality function."""

    def test_score_content_quality_returns_float(
        self, sample_content: str
    ) -> None:
        """score_content_quality should return a float score."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.85}'
            result = score_content_quality(sample_content)
            assert isinstance(result, float)

    def test_score_content_quality_high_quality(
        self, sample_content: str
    ) -> None:
        """High-quality content should receive a high score."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.92}'
            result = score_content_quality(sample_content)
            assert result >= 0.8

    def test_score_content_quality_low_quality(
        self, low_quality_content: str
    ) -> None:
        """Low-quality content should receive a low score."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.15}'
            result = score_content_quality(low_quality_content)
            assert result < 0.4

    def test_score_content_quality_empty_content(
        self, empty_content: str
    ) -> None:
        """Empty content should receive a very low or zero score."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.0}'
            result = score_content_quality(empty_content)
            assert result <= 0.1

    def test_score_content_quality_score_range(
        self, sample_content: str
    ) -> None:
        """Score should always be between 0.0 and 1.0."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.5}'
            result = score_content_quality(sample_content)
            assert 0.0 <= result <= 1.0

    def test_score_content_quality_calls_llm(
        self, sample_content: str
    ) -> None:
        """score_content_quality should invoke the LLM backend."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.75}'
            score_content_quality(sample_content)
            mock_call.assert_called_once()

    def test_score_content_quality_with_context(
        self, sample_content: str
    ) -> None:
        """score_content_quality should accept optional context parameter."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.80}'
            result = score_content_quality(
                sample_content, context="product review"
            )
            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0

    def test_score_content_quality_handles_malformed_response(
        self, sample_content: str
    ) -> None:
        """Malformed LLM response should not crash the function."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = "not valid json"
            with pytest.raises((ValueError, KeyError, TypeError)):
                score_content_quality(sample_content)

    def test_score_content_quality_very_long_content(self) -> None:
        """Very long content should still be scored without error."""
        long_content = "word " * 10000
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.65}'
            result = score_content_quality(long_content)
            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# Tests for get_quality_metrics
# ---------------------------------------------------------------------------


class TestGetQualityMetrics:
    """Tests for the get_quality_metrics function."""

    def test_get_quality_metrics_returns_dict(
        self, sample_content: str
    ) -> None:
        """get_quality_metrics should return a dictionary."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {"readability": 0.9, "engagement": 0.8}}'
            )
            result = get_quality_metrics(sample_content)
            assert isinstance(result, dict)

    def test_get_quality_metrics_contains_expected_keys(
        self, sample_content: str
    ) -> None:
        """Metrics dict should contain standard quality dimensions."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {'
                '"readability": 0.9, '
                '"engagement": 0.8, '
                '"originality": 0.85, '
                '"depth": 0.75'
                '}}'
            )
            result = get_quality_metrics(sample_content)
            expected_keys = {"readability", "engagement", "originality", "depth"}
            assert expected_keys.issubset(result.keys())

    def test_get_quality_metrics_values_in_range(
        self, sample_content: str
    ) -> None:
        """All metric values should be between 0.0 and 1.0."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {'
                '"readability": 0.9, '
                '"engagement": 0.8, '
                '"originality": 0.85, '
                '"depth": 0.75'
                '}}'
            )
            result = get_quality_metrics(sample_content)
            for key, value in result.items():
                assert 0.0 <= value <= 1.0, f"{key}={value} out of range"

    def test_get_quality_metrics_low_quality_content(
        self, low_quality_content: str
    ) -> None:
        """Low-quality content should have low metric values."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {'
                '"readability": 0.2, '
                '"engagement": 0.15, '
                '"originality": 0.25, '
                '"depth": 0.1'
                '}}'
            )
            result = get_quality_metrics(low_quality_content)
            for value in result.values():
                assert value < 0.5

    def test_get_quality_metrics_empty_content(
        self, empty_content: str
    ) -> None:
        """Empty content should produce zero or near-zero metrics."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {'
                '"readability": 0.0, '
                '"engagement": 0.0, '
                '"originality": 0.0, '
                '"depth": 0.0'
                '}}'
            )
            result = get_quality_metrics(empty_content)
            for value in result.values():
                assert value <= 0.1

    def test_get_quality_metrics_calls_llm(
        self, sample_content: str
    ) -> None:
        """get_quality_metrics should invoke the LLM backend."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"metrics": {"readability": 0.5}}'
            get_quality_metrics(sample_content)
            mock_call.assert_called_once()

    def test_get_quality_metrics_with_custom_metrics(
        self, sample_content: str
    ) -> None:
        """get_quality_metrics should support custom metric requests."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"metrics": {"readability": 0.88, "tone": 0.72}}'
            )
            result = get_quality_metrics(
                sample_content, metrics=["readability", "tone"]
            )
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_get_quality_metrics_handles_missing_metrics_key(
        self, sample_content: str
    ) -> None:
        """Response missing 'metrics' key should raise an error."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.5}'
            with pytest.raises((KeyError, ValueError)):
                get_quality_metrics(sample_content)


# ---------------------------------------------------------------------------
# Tests for flag_low_quality
# ---------------------------------------------------------------------------


class TestFlagLowQuality:
    """Tests for the flag_low_quality function."""

    def test_flag_low_quality_returns_bool(
        self, sample_content: str
    ) -> None:
        """flag_low_quality should return a boolean."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.85, "flags": []}'
            result = flag_low_quality(sample_content)
            assert isinstance(result, bool)

    def test_flag_low_quality_true_for_bad_content(
        self, low_quality_content: str
    ) -> None:
        """Low-quality content should be flagged."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"score": 0.2, "flags": ["too_short", "low_engagement"]}'
            )
            result = flag_low_quality(low_quality_content)
            assert result is True

    def test_flag_low_quality_false_for_good_content(
        self, sample_content: str
    ) -> None:
        """High-quality content should not be flagged."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.9, "flags": []}'
            result = flag_low_quality(sample_content)
            assert result is False

    def test_flag_low_quality_empty_content(
        self, empty_content: str
    ) -> None:
        """Empty content should always be flagged as low quality."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.0, "flags": ["empty"]}'
            result = flag_low_quality(empty_content)
            assert result is True

    def test_flag_low_quality_respects_threshold(
        self, sample_content: str
    ) -> None:
        """Content below the threshold should be flagged."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.45, "flags": ["below_threshold"]}'
            result = flag_low_quality(sample_content, threshold=0.6)
            assert result is True

    def test_flag_low_quality_custom_threshold(
        self, sample_content: str
    ) -> None:
        """Custom threshold should be respected."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.70, "flags": []}'
            result = flag_low_quality(sample_content, threshold=0.8)
            assert result is True

    def test_flag_low_quality_calls_llm(
        self, sample_content: str
    ) -> None:
        """flag_low_quality should invoke the LLM backend."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.5, "flags": []}'
            flag_low_quality(sample_content)
            mock_call.assert_called_once()

    def test_flag_low_quality_with_flags_list(
        self, low_quality_content: str
    ) -> None:
        """Content with quality flags should be flagged."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = (
                '{"score": 0.5, "flags": ["plagiarism", "spam"]}'
            )
            result = flag_low_quality(low_quality_content)
            assert result is True

    def test_flag_low_quality_handles_malformed_response(
        self, sample_content: str
    ) -> None:
        """Malformed LLM response should raise an error."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = "not valid json"
            with pytest.raises((ValueError, KeyError, TypeError)):
                flag_low_quality(sample_content)

    def test_flag_low_quality_boundary_score(
        self, sample_content: str
    ) -> None:
        """Score exactly at threshold should not be flagged."""
        with patch(
            "src.ugc_marketplace.agents.quality_scoring._call_llm"
        ) as mock_call:
            mock_call.return_value = '{"score": 0.6, "flags": []}'
            result = flag_low_quality(sample_content, threshold=0.6)
            assert result is False
