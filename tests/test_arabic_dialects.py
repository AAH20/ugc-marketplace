"""Tests for Arabic dialect detection and definitions."""
import pytest
from app.arabic.dialects import (
    ArabicDialect,
    DialectDetector,
    get_dialect,
    get_dialect_region,
    get_dialect_greeting,
    is_valid_dialect,
)


class TestArabicDialectEnum:
    """Test ArabicDialect enum values."""

    def test_egyptian_dialect_exists(self):
        assert ArabicDialect.EGYPTIAN.value == "egyptian"

    def test_gulf_dialect_exists(self):
        assert ArabicDialect.GULF.value == "gulf"

    def test_levantine_dialect_exists(self):
        assert ArabicDialect.LEVANTINE.value == "levantine"

    def test_maghrebi_dialect_exists(self):
        assert ArabicDialect.MAGHREBI.value == "maghrebi"

    def test_all_four_dialects_present(self):
        values = [d.value for d in ArabicDialect]
        assert len(values) == 4
        assert "egyptian" in values
        assert "gulf" in values
        assert "levantine" in values
        assert "maghrebi" in values


class TestDialectDetection:
    """Test dialect detection from text."""

    def test_detect_egyptian_greeting(self):
        detector = DialectDetector()
        result = detector.detect("أهلا بيك")
        assert result == ArabicDialect.EGYPTIAN

    def test_detect_gulf_greeting(self):
        detector = DialectDetector()
        result = detector.detect("هلا فيك")
        assert result == ArabicDialect.GULF

    def test_detect_levantine_greeting(self):
        detector = DialectDetector()
        result = detector.detect("أهلا وسهلا فيك")
        assert result == ArabicDialect.LEVANTINE

    def test_detect_maghrebi_greeting(self):
        detector = DialectDetector()
        result = detector.detect("مرحبا بيك")
        assert result == ArabicDialect.MAGHREBI

    def test_detect_egyptian_pronoun(self):
        detector = DialectDetector()
        result = detector.detect("إزيك")
        assert result == ArabicDialect.EGYPTIAN

    def test_detect_gulf_pronoun(self):
        detector = DialectDetector()
        result = detector.detect("شلونك")
        assert result == ArabicDialect.GULF

    def test_detect_levantine_word(self):
        detector = DialectDetector()
        result = detector.detect("كتير")
        assert result == ArabicDialect.LEVANTINE

    def test_detect_maghrebi_word(self):
        detector = DialectDetector()
        result = detector.detect("بزاف")
        assert result == ArabicDialect.MAGHREBI

    def test_detect_default_when_no_match(self):
        detector = DialectDetector()
        result = detector.detect("مرحبا")
        assert result == ArabicDialect.EGYPTIAN  # Default fallback

    def test_detect_empty_string_returns_default(self):
        detector = DialectDetector()
        result = detector.detect("")
        assert result == ArabicDialect.EGYPTIAN


class TestGetDialect:
    """Test get_dialect convenience function."""

    def test_get_dialect_returns_enum(self):
        result = get_dialect("أهلا بيك")
        assert result == ArabicDialect.EGYPTIAN

    def test_get_dialect_returns_gulf(self):
        result = get_dialect("هلا فيك")
        assert result == ArabicDialect.GULF


class TestDialectRegion:
    """Test dialect to region mapping."""

    def test_egyptian_region(self):
        assert get_dialect_region(ArabicDialect.EGYPTIAN) == "Egypt"

    def test_gulf_region(self):
        assert get_dialect_region(ArabicDialect.GULF) == "Gulf"

    def test_levantine_region(self):
        assert get_dialect_region(ArabicDialect.LEVANTINE) == "Levant"

    def test_maghrebi_region(self):
        assert get_dialect_region(ArabicDialect.MAGHREBI) == "Maghreb"


class TestDialectGreeting:
    """Test dialect-specific greetings."""

    def test_egyptian_greeting(self):
        assert get_dialect_greeting(ArabicDialect.EGYPTIAN) == "أهلا بيك"

    def test_gulf_greeting(self):
        assert get_dialect_greeting(ArabicDialect.GULF) == "هلا فيك"

    def test_levantine_greeting(self):
        assert get_dialect_greeting(ArabicDialect.LEVANTINE) == "أهلا وسهلا"

    def test_maghrebi_greeting(self):
        assert get_dialect_greeting(ArabicDialect.MAGHREBI) == "مرحبا بيك"


class TestIsValidDialect:
    """Test dialect validation."""

    def test_valid_dialect_string(self):
        assert is_valid_dialect("egyptian") is True

    def test_valid_gulf(self):
        assert is_valid_dialect("gulf") is True

    def test_valid_levantine(self):
        assert is_valid_dialect("levantine") is True

    def test_valid_maghrebi(self):
        assert is_valid_dialect("maghrebi") is True

    def test_invalid_dialect(self):
        assert is_valid_dialect("french") is False

    def test_empty_string_invalid(self):
        assert is_valid_dialect("") is False
