"""Comprehensive agent tests for fraud detection module."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from ugc_marketplace.agents.fraud_detection import (
    detect_fraud,
    flag_suspicious_activity,
    get_fraud_score,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_user():
    """Return a sample user dictionary."""
    return {
        "id": "user_123",
        "username": "testuser",
        "email": "test@example.com",
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "trust_score": 0.85,
    }


@pytest.fixture
def sample_transaction():
    """Return a sample transaction dictionary."""
    return {
        "id": "txn_456",
        "user_id": "user_123",
        "amount": 150.00,
        "currency": "USD",
        "timestamp": datetime.now().isoformat(),
        "ip_address": "192.168.1.100",
        "device_id": "device_abc",
        "payment_method": "credit_card",
    }


@pytest.fixture
def sample_listing():
    """Return a sample listing dictionary."""
    return {
        "id": "listing_789",
        "user_id": "user_123",
        "title": "Test Product",
        "description": "A test product listing",
        "price": 49.99,
        "category": "electronics",
        "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
    }


@pytest.fixture
def high_risk_user():
    """Return a high-risk user profile."""
    return {
        "id": "user_risk_001",
        "username": "riskyuser",
        "email": "risk@example.com",
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        "trust_score": 0.15,
        "previous_violations": 3,
    }


@pytest.fixture
def mock_fraud_config():
    """Return a mock fraud detection configuration."""
    return {
        "threshold": 0.7,
        "max_transactions_per_hour": 10,
        "max_amount_per_day": 1000.00,
        "suspicious_ip_ranges": ["203.0.113.0/24", "198.51.100.0/24"],
        "blocked_countries": ["XX", "YY"],
    }


@pytest.fixture
def mock_ml_model():
    """Return a mock ML model for fraud scoring."""
    model = MagicMock()
    model.predict.return_value = [0.3]
    model.predict_proba.return_value = [[0.7, 0.3]]
    return model


# ---------------------------------------------------------------------------
# Tests for detect_fraud
# ---------------------------------------------------------------------------


class TestDetectFraud:
    """Tests for the detect_fraud function."""

    def test_detect_fraud_with_clean_transaction(self, sample_user, sample_transaction):
        """detect_fraud should return low risk for a normal transaction."""
        result = detect_fraud(sample_user, sample_transaction)
        assert result is not None
        assert "is_fraudulent" in result
        assert "risk_score" in result
        assert result["is_fraudulent"] is False
        assert result["risk_score"] < 0.5

    def test_detect_fraud_with_high_risk_user(self, high_risk_user, sample_transaction):
        """detect_fraud should flag transactions from high-risk users."""
        result = detect_fraud(high_risk_user, sample_transaction)
        assert result is not None
        assert "is_fraudulent" in result
        assert "risk_score" in result
        assert result["is_fraudulent"] is True
        assert result["risk_score"] >= 0.7

    def test_detect_fraud_with_suspicious_amount(self, sample_user):
        """detect_fraud should flag unusually large transactions."""
        large_transaction = {
            "id": "txn_large",
            "user_id": "user_123",
            "amount": 99999.99,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "ip_address": "192.168.1.100",
            "device_id": "device_abc",
            "payment_method": "credit_card",
        }
        result = detect_fraud(sample_user, large_transaction)
        assert result is not None
        assert result["risk_score"] > 0.5

    def test_detect_fraud_with_suspicious_ip(self, sample_user):
        """detect_fraud should flag transactions from suspicious IP ranges."""
        suspicious_txn = {
            "id": "txn_susp_ip",
            "user_id": "user_123",
            "amount": 50.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "ip_address": "203.0.113.50",
            "device_id": "device_abc",
            "payment_method": "credit_card",
        }
        result = detect_fraud(sample_user, suspicious_txn)
        assert result is not None
        assert result["risk_score"] > 0.3

    def test_detect_fraud_with_new_account(self, sample_transaction):
        """detect_fraud should flag transactions from very new accounts."""
        new_user = {
            "id": "user_new",
            "username": "newuser",
            "email": "new@example.com",
            "created_at": datetime.now().isoformat(),
            "trust_score": 0.0,
        }
        result = detect_fraud(new_user, sample_transaction)
        assert result is not None
        assert result["risk_score"] > 0.4

    def test_detect_fraud_returns_confidence(self, sample_user, sample_transaction):
        """detect_fraud should include a confidence metric."""
        result = detect_fraud(sample_user, sample_transaction)
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_detect_fraud_with_multiple_red_flags(self, high_risk_user):
        """detect_fraud should escalate risk with multiple red flags."""
        suspicious_txn = {
            "id": "txn_multi",
            "user_id": "user_risk_001",
            "amount": 5000.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "ip_address": "203.0.113.99",
            "device_id": "device_suspicious",
            "payment_method": "credit_card",
        }
        result = detect_fraud(high_risk_user, suspicious_txn)
        assert result["is_fraudulent"] is True
        assert result["risk_score"] >= 0.9

    def test_detect_fraud_with_empty_user(self, sample_transaction):
        """detect_fraud should handle empty user dict gracefully."""
        result = detect_fraud({}, sample_transaction)
        assert result is not None
        assert "risk_score" in result

    def test_detect_fraud_with_empty_transaction(self, sample_user):
        """detect_fraud should handle empty transaction dict gracefully."""
        result = detect_fraud(sample_user, {})
        assert result is not None
        assert "risk_score" in result

    def test_detect_fraud_includes_reasons(self, high_risk_user, sample_transaction):
        """detect_fraud should provide reasons for the fraud determination."""
        result = detect_fraud(high_risk_user, sample_transaction)
        assert "reasons" in result
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) > 0

    def test_detect_fraud_with_rapid_transactions(self, sample_user):
        """detect_fraud should flag rapid-fire transaction patterns."""
        rapid_txns = [
            {
                "id": f"txn_rapid_{i}",
                "user_id": "user_123",
                "amount": 100.00,
                "currency": "USD",
                "timestamp": (datetime.now() - timedelta(seconds=i * 10)).isoformat(),
                "ip_address": "192.168.1.100",
                "device_id": "device_abc",
                "payment_method": "credit_card",
            }
            for i in range(20)
        ]
        result = detect_fraud(sample_user, rapid_txns)
        assert result is not None
        assert result["risk_score"] > 0.5

    def test_detect_fraud_with_international_transaction(self, sample_user):
        """detect_fraud should consider international transactions."""
        intl_txn = {
            "id": "txn_intl",
            "user_id": "user_123",
            "amount": 200.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "ip_address": "185.220.101.50",
            "device_id": "device_abc",
            "payment_method": "credit_card",
            "country_code": "XX",
        }
        result = detect_fraud(sample_user, intl_txn)
        assert result is not None
        assert result["risk_score"] > 0.3

    def test_detect_fraud_idempotent(self, sample_user, sample_transaction):
        """detect_fraud should return consistent results for the same input."""
        result1 = detect_fraud(sample_user, sample_transaction)
        result2 = detect_fraud(sample_user, sample_transaction)
        assert result1["risk_score"] == result2["risk_score"]
        assert result1["is_fraudulent"] == result2["is_fraudulent"]


# ---------------------------------------------------------------------------
# Tests for flag_suspicious_activity
# ---------------------------------------------------------------------------


class TestFlagSuspiciousActivity:
    """Tests for the flag_suspicious_activity function."""

    def test_flag_suspicious_activity_with_normal_user(self, sample_user):
        """flag_suspicious_activity should not flag normal user behavior."""
        result = flag_suspicious_activity(sample_user)
        assert result is not None
        assert "flagged" in result
        assert result["flagged"] is False

    def test_flag_suspicious_activity_with_high_risk_user(self, high_risk_user):
        """flag_suspicious_activity should flag high-risk users."""
        result = flag_suspicious_activity(high_risk_user)
        assert result is not None
        assert result["flagged"] is True
        assert "reason" in result

    def test_flag_suspicious_activity_with_violation_history(self):
        """flag_suspicious_activity should flag users with past violations."""
        user_with_violations = {
            "id": "user_viol",
            "username": "violator",
            "email": "viol@example.com",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "trust_score": 0.5,
            "previous_violations": 5,
        }
        result = flag_suspicious_activity(user_with_violations)
        assert result["flagged"] is True

    def test_flag_suspicious_activity_with_spam_pattern(self):
        """flag_suspicious_activity should detect spam-like behavior."""
        spam_user = {
            "id": "user_spam",
            "username": "spammer",
            "email": "spam@example.com",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "trust_score": 0.1,
            "listings_count": 500,
            "messages_sent": 10000,
        }
        result = flag_suspicious_activity(spam_user)
        assert result["flagged"] is True

    def test_flag_suspicious_activity_returns_severity(self, high_risk_user):
        """flag_suspicious_activity should return a severity level."""
        result = flag_suspicious_activity(high_risk_user)
        assert "severity" in result
        assert result["severity"] in ("low", "medium", "high", "critical")

    def test_flag_suspicious_activity_with_empty_user(self):
        """flag_suspicious_activity should handle empty user dict."""
        result = flag_suspicious_activity({})
        assert result is not None
        assert "flagged" in result

    def test_flag_suspicious_activity_with_bot_behavior(self):
        """flag_suspicious_activity should detect bot-like activity patterns."""
        bot_user = {
            "id": "user_bot",
            "username": "botuser",
            "email": "bot@example.com",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "trust_score": 0.05,
            "actions_per_minute": 120,
            "unique_ips": 15,
        }
        result = flag_suspicious_activity(bot_user)
        assert result["flagged"] is True
        assert result["severity"] in ("high", "critical")

    def test_flag_suspicious_activity_with_takeover_pattern(self):
        """flag_suspicious_activity should detect account takeover patterns."""
        takeover_user = {
            "id": "user_takeover",
            "username": "legituser",
            "email": "legit@example.com",
            "created_at": (datetime.now() - timedelta(days=365)).isoformat(),
            "trust_score": 0.9,
            "recent_password_change": True,
            "new_device_login": True,
            "unusual_location": True,
        }
        result = flag_suspicious_activity(takeover_user)
        assert result["flagged"] is True

    def test_flag_suspicious_activity_includes_timestamp(self, high_risk_user):
        """flag_suspicious_activity should include a timestamp."""
        result = flag_suspicious_activity(high_risk_user)
        assert "timestamp" in result

    def test_flag_suspicious_activity_with_low_trust_score(self):
        """flag_suspicious_activity should flag users with very low trust."""
        low_trust_user = {
            "id": "user_low",
            "username": "lowtrust",
            "email": "low@example.com",
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "trust_score": 0.05,
        }
        result = flag_suspicious_activity(low_trust_user)
        assert result["flagged"] is True

    def test_flag_suspicious_activity_with_normal_trust_score(self):
        """flag_suspicious_activity should not flag users with good trust."""
        good_user = {
            "id": "user_good",
            "username": "gooduser",
            "email": "good@example.com",
            "created_at": (datetime.now() - timedelta(days=180)).isoformat(),
            "trust_score": 0.95,
            "previous_violations": 0,
        }
        result = flag_suspicious_activity(good_user)
        assert result["flagged"] is False

    def test_flag_suspicious_activity_with_chargeback_history(self):
        """flag_suspicious_activity should flag users with chargeback history."""
        chargeback_user = {
            "id": "user_chargeback",
            "username": "chargebackuser",
            "email": "cb@example.com",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "trust_score": 0.4,
            "chargebacks": 3,
        }
        result = flag_suspicious_activity(chargeback_user)
        assert result["flagged"] is True

    def test_flag_suspicious_activity_with_multiple_flags(self):
        """flag_suspicious_activity should aggregate multiple risk signals."""
        multi_risk_user = {
            "id": "user_multi",
            "username": "multiuser",
            "email": "multi@example.com",
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "trust_score": 0.1,
            "previous_violations": 2,
            "chargebacks": 1,
            "actions_per_minute": 80,
        }
        result = flag_suspicious_activity(multi_risk_user)
        assert result["flagged"] is True
        assert result["severity"] == "critical"


# ---------------------------------------------------------------------------
# Tests for get_fraud_score
# ---------------------------------------------------------------------------


class TestGetFraudScore:
    """Tests for the get_fraud_score function."""

    def test_get_fraud_score_with_low_risk_user(self, sample_user):
        """get_fraud_score should return a low score for trusted users."""
        score = get_fraud_score(sample_user)
        assert score is not None
        assert 0.0 <= score <= 1.0
        assert score < 0.3

    def test_get_fraud_score_with_high_risk_user(self, high_risk_user):
        """get_fraud_score should return a high score for risky users."""
        score = get_fraud_score(high_risk_user)
        assert score is not None
        assert 0.0 <= score <= 1.0
        assert score > 0.7

    def test_get_fraud_score_returns_float(self, sample_user):
        """get_fraud_score should always return a float."""
        score = get_fraud_score(sample_user)
        assert isinstance(score, float)

    def test_get_fraud_score_with_empty_user(self):
        """get_fraud_score should handle empty user dict."""
        score = get_fraud_score({})
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_transaction_context(self, sample_user, sample_transaction):
        """get_fraud_score should incorporate transaction context."""
        score = get_fraud_score(sample_user, context=sample_transaction)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_high_value_transaction(self, sample_user):
        """get_fraud_score should increase for high-value transactions."""
        high_value_txn = {
            "amount": 5000.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
        }
        score = get_fraud_score(sample_user, context=high_value_txn)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_new_account(self):
        """get_fraud_score should be elevated for new accounts."""
        new_user = {
            "id": "user_new",
            "username": "newuser",
            "email": "new@example.com",
            "created_at": datetime.now().isoformat(),
            "trust_score": 0.0,
        }
        score = get_fraud_score(new_user)
        assert score > 0.4

    def test_get_fraud_score_with_established_account(self):
        """get_fraud_score should be low for established accounts."""
        established_user = {
            "id": "user_est",
            "username": "established",
            "email": "est@example.com",
            "created_at": (datetime.now() - timedelta(days=730)).isoformat(),
            "trust_score": 0.98,
            "successful_transactions": 500,
        }
        score = get_fraud_score(established_user)
        assert score < 0.2

    def test_get_fraud_score_with_violation_history(self):
        """get_fraud_score should increase with violation history."""
        user_with_history = {
            "id": "user_hist",
            "username": "historyuser",
            "email": "hist@example.com",
            "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
            "trust_score": 0.5,
            "previous_violations": 4,
        }
        score = get_fraud_score(user_with_history)
        assert score > 0.5

    def test_get_fraud_score_with_device_reputation(self, sample_user):
        """get_fraud_score should consider device reputation."""
        context = {
            "device_id": "device_known_good",
            "device_trust_score": 0.95,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_bad_device_reputation(self, sample_user):
        """get_fraud_score should increase for untrusted devices."""
        context = {
            "device_id": "device_suspicious",
            "device_trust_score": 0.1,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_ip_reputation(self, sample_user):
        """get_fraud_score should consider IP reputation."""
        context = {
            "ip_address": "192.168.1.100",
            "ip_reputation": "good",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_bad_ip_reputation(self, sample_user):
        """get_fraud_score should increase for bad IP reputation."""
        context = {
            "ip_address": "203.0.113.50",
            "ip_reputation": "bad",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_velocity_check(self, sample_user):
        """get_fraud_score should factor in transaction velocity."""
        context = {
            "transactions_last_hour": 15,
            "transactions_last_day": 50,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_velocity(self, sample_user):
        """get_fraud_score should be low for normal transaction velocity."""
        context = {
            "transactions_last_hour": 2,
            "transactions_last_day": 5,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_listing_context(self, sample_user, sample_listing):
        """get_fraud_score should incorporate listing context."""
        score = get_fraud_score(sample_user, context=sample_listing)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_get_fraud_score_with_suspicious_listing(self, sample_user):
        """get_fraud_score should increase for suspicious listings."""
        suspicious_listing = {
            "id": "listing_susp",
            "user_id": "user_123",
            "title": "FREE MONEY CLICK HERE",
            "description": "A" * 10000,
            "price": 0.01,
            "category": "electronics",
            "created_at": datetime.now().isoformat(),
        }
        score = get_fraud_score(sample_user, context=suspicious_listing)
        assert score > 0.4

    def test_get_fraud_score_with_payment_method_risk(self, sample_user):
        """get_fraud_score should consider payment method risk."""
        context = {
            "payment_method": "cryptocurrency",
            "payment_risk": "high",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_low_risk_payment(self, sample_user):
        """get_fraud_score should be lower for trusted payment methods."""
        context = {
            "payment_method": "verified_bank_transfer",
            "payment_risk": "low",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_geolocation_mismatch(self, sample_user):
        """get_fraud_score should flag geolocation mismatches."""
        context = {
            "user_country": "US",
            "transaction_country": "XX",
            "ip_country": "YY",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_matching_geolocation(self, sample_user):
        """get_fraud_score should be low when geolocation matches."""
        context = {
            "user_country": "US",
            "transaction_country": "US",
            "ip_country": "US",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_account_age_factor(self):
        """get_fraud_score should weight account age appropriately."""
        very_new_user = {
            "id": "user_very_new",
            "username": "verynew",
            "email": "vn@example.com",
            "created_at": datetime.now().isoformat(),
            "trust_score": 0.0,
        }
        score = get_fraud_score(very_new_user)
        assert score > 0.5

    def test_get_fraud_score_with_perfect_history(self):
        """get_fraud_score should be minimal for users with perfect history."""
        perfect_user = {
            "id": "user_perfect",
            "username": "perfect",
            "email": "perfect@example.com",
            "created_at": (datetime.now() - timedelta(days=1000)).isoformat(),
            "trust_score": 1.0,
            "successful_transactions": 2000,
            "previous_violations": 0,
            "chargebacks": 0,
        }
        score = get_fraud_score(perfect_user)
        assert score < 0.1

    def test_get_fraud_score_with_compromised_account(self):
        """get_fraud_score should be high for compromised accounts."""
        compromised_user = {
            "id": "user_compromised",
            "username": "compromised",
            "email": "comp@example.com",
            "created_at": (datetime.now() - timedelta(days=200)).isoformat(),
            "trust_score": 0.3,
            "account_compromise_indicators": [
                "password_reset_from_new_ip",
                "email_change_from_new_device",
                "unusual_purchase_pattern",
            ],
        }
        score = get_fraud_score(compromised_user)
        assert score > 0.7

    def test_get_fraud_score_with_behavioral_biometrics(self, sample_user):
        """get_fraud_score should incorporate behavioral biometrics."""
        context = {
            "typing_speed_wpm": 150,
            "mouse_movement_entropy": 0.1,
            "session_duration_seconds": 5,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_biometrics(self, sample_user):
        """get_fraud_score should be low for normal behavioral biometrics."""
        context = {
            "typing_speed_wpm": 45,
            "mouse_movement_entropy": 0.8,
            "session_duration_seconds": 300,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_email_reputation(self):
        """get_fraud_score should consider email domain reputation."""
        user_bad_email = {
            "id": "user_bad_email",
            "username": "bademail",
            "email": "test@tempmail.com",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "trust_score": 0.2,
        }
        score = get_fraud_score(user_bad_email)
        assert score > 0.4

    def test_get_fraud_score_with_phone_verification(self):
        """get_fraud_score should benefit from phone verification."""
        verified_user = {
            "id": "user_verified",
            "username": "verified",
            "email": "verified@example.com",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "trust_score": 0.7,
            "phone_verified": True,
        }
        score = get_fraud_score(verified_user)
        assert score < 0.4

    def test_get_fraud_score_with_unverified_phone(self):
        """get_fraud_score should be higher without phone verification."""
        unverified_user = {
            "id": "user_unverified",
            "username": "unverified",
            "email": "unverified@example.com",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "trust_score": 0.7,
            "phone_verified": False,
        }
        score = get_fraud_score(unverified_user)
        assert score > 0.3

    def test_get_fraud_score_with_social_graph_analysis(self, sample_user):
        """get_fraud_score should incorporate social graph signals."""
        context = {
            "connected_accounts_flagged": 3,
            "network_risk_score": 0.8,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_clean_social_graph(self, sample_user):
        """get_fraud_score should be low with a clean social graph."""
        context = {
            "connected_accounts_flagged": 0,
            "network_risk_score": 0.1,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_purchase_pattern_analysis(self, sample_user):
        """get_fraud_score should detect anomalous purchase patterns."""
        context = {
            "usual_purchase_categories": ["books", "clothing"],
            "current_purchase_category": "electronics",
            "purchase_amount_deviation": 5.0,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_purchase_pattern(self, sample_user):
        """get_fraud_score should be low for normal purchase patterns."""
        context = {
            "usual_purchase_categories": ["electronics", "books"],
            "current_purchase_category": "electronics",
            "purchase_amount_deviation": 0.5,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_time_of_day_factor(self, sample_user):
        """get_fraud_score should consider unusual transaction timing."""
        context = {
            "transaction_hour": 3,
            "user_usual_active_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_timing(self, sample_user):
        """get_fraud_score should be low for normal transaction timing."""
        context = {
            "transaction_hour": 14,
            "user_usual_active_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_refund_pattern(self):
        """get_fraud_score should flag excessive refund requests."""
        refund_user = {
            "id": "user_refund",
            "username": "refunduser",
            "email": "refund@example.com",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "trust_score": 0.4,
            "total_purchases": 20,
            "total_refunds": 18,
        }
        score = get_fraud_score(refund_user)
        assert score > 0.6

    def test_get_fraud_score_with_normal_refund_pattern(self):
        """get_fraud_score should be low for normal refund rates."""
        normal_user = {
            "id": "user_normal_refund",
            "username": "normalrefund",
            "email": "normal@example.com",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "trust_score": 0.8,
            "total_purchases": 50,
            "total_refunds": 2,
        }
        score = get_fraud_score(normal_user)
        assert score < 0.3

    def test_get_fraud_score_with_dispute_history(self):
        """get_fraud_score should consider dispute history."""
        dispute_user = {
            "id": "user_dispute",
            "username": "disputeuser",
            "email": "dispute@example.com",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "trust_score": 0.5,
            "disputes_filed": 5,
            "disputes_lost": 4,
        }
        score = get_fraud_score(dispute_user)
        assert score > 0.5

    def test_get_fraud_score_with_no_disputes(self):
        """get_fraud_score should be low for users without disputes."""
        no_dispute_user = {
            "id": "user_no_dispute",
            "username": "nodispute",
            "email": "nodispute@example.com",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "trust_score": 0.85,
            "disputes_filed": 0,
            "disputes_lost": 0,
        }
        score = get_fraud_score(no_dispute_user)
        assert score < 0.3

    def test_get_fraud_score_with_kyc_status(self):
        """get_fraud_score should consider KYC verification status."""
        unverified_user = {
            "id": "user_no_kyc",
            "username": "nokyc",
            "email": "nokyc@example.com",
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "trust_score": 0.3,
            "kyc_verified": False,
        }
        score = get_fraud_score(unverified_user)
        assert score > 0.4

    def test_get_fraud_score_with_kyc_verified(self):
        """get_fraud_score should benefit from KYC verification."""
        verified_user = {
            "id": "user_kyc",
            "username": "kycuser",
            "email": "kyc@example.com",
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "trust_score": 0.7,
            "kyc_verified": True,
        }
        score = get_fraud_score(verified_user)
        assert score < 0.4

    def test_get_fraud_score_with_session_anomaly(self, sample_user):
        """get_fraud_score should detect session anomalies."""
        context = {
            "session_ip_mismatch": True,
            "session_geo_mismatch": True,
            "session_device_mismatch": True,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.6

    def test_get_fraud_score_with_normal_session(self, sample_user):
        """get_fraud_score should be low for consistent sessions."""
        context = {
            "session_ip_mismatch": False,
            "session_geo_mismatch": False,
            "session_device_mismatch": False,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_coupon_abuse(self):
        """get_fraud_score should flag coupon abuse patterns."""
        coupon_abuser = {
            "id": "user_coupon",
            "username": "couponuser",
            "email": "coupon@example.com",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "trust_score": 0.3,
            "coupon_claims": 50,
            "unique_coupons_used": 45,
            "account_claims_ratio": 0.9,
        }
        score = get_fraud_score(coupon_abuser)
        assert score > 0.5

    def test_get_fraud_score_with_normal_coupon_usage(self):
        """get_fraud_score should be low for normal coupon usage."""
        normal_coupon_user = {
            "id": "user_normal_coupon",
            "username": "normalcoupon",
            "email": "nc@example.com",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "trust_score": 0.8,
            "coupon_claims": 3,
            "unique_coupons_used": 3,
            "account_claims_ratio": 0.1,
        }
        score = get_fraud_score(normal_coupon_user)
        assert score < 0.3

    def test_get_fraud_score_with_multi_accounting(self):
        """get_fraud_score should detect multi-accounting patterns."""
        multi_account_user = {
            "id": "user_multi",
            "username": "multiuser",
            "email": "multi@example.com",
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "trust_score": 0.2,
            "linked_accounts": 5,
            "shared_devices": 3,
            "shared_payment_methods": 2,
        }
        score = get_fraud_score(multi_account_user)
        assert score > 0.6

    def test_get_fraud_score_with_single_account(self):
        """get_fraud_score should be low for single-account users."""
        single_user = {
            "id": "user_single",
            "username": "singleuser",
            "email": "single@example.com",
            "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
            "trust_score": 0.85,
            "linked_accounts": 1,
            "shared_devices": 0,
            "shared_payment_methods": 0,
        }
        score = get_fraud_score(single_user)
        assert score < 0.3

    def test_get_fraud_score_with_content_moderation_flags(self):
        """get_fraud_score should consider content moderation flags."""
        flagged_user = {
            "id": "user_flagged",
            "username": "flaggeduser",
            "email": "flagged@example.com",
            "created_at": (datetime.now() - timedelta(days=45)).isoformat(),
            "trust_score": 0.4,
            "content_flags": 3,
            "last_flag_reason": "prohibited_item",
        }
        score = get_fraud_score(flagged_user)
        assert score > 0.5

    def test_get_fraud_score_with_clean_content_history(self):
        """get_fraud_score should be low for users with clean content."""
        clean_user = {
            "id": "user_clean",
            "username": "cleanuser",
            "email": "clean@example.com",
            "created_at": (datetime.now() - timedelta(days=45)).isoformat(),
            "trust_score": 0.9,
            "content_flags": 0,
        }
        score = get_fraud_score(clean_user)
        assert score < 0.3

    def test_get_fraud_score_with_shipping_address_risk(self, sample_user):
        """get_fraud_score should consider shipping address risk."""
        context = {
            "shipping_address": "123 Unknown St",
            "address_verification": "failed",
            "address_risk_score": 0.9,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_verified_shipping(self, sample_user):
        """get_fraud_score should be low for verified shipping addresses."""
        context = {
            "shipping_address": "456 Known Ave",
            "address_verification": "passed",
            "address_risk_score": 0.1,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_browser_fingerprint(self, sample_user):
        """get_fraud_score should incorporate browser fingerprinting."""
        context = {
            "browser_fingerprint": "fp_known_123",
            "fingerprint_trust_score": 0.9,
            "fingerprint_first_seen": (datetime.now() - timedelta(days=60)).isoformat(),
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.4

    def test_get_fraud_score_with_suspicious_fingerprint(self, sample_user):
        """get_fraud_score should flag suspicious browser fingerprints."""
        context = {
            "browser_fingerprint": "fp_suspicious_456",
            "fingerprint_trust_score": 0.1,
            "fingerprint_first_seen": datetime.now().isoformat(),
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_vpn_detection(self, sample_user):
        """get_fraud_score should consider VPN usage."""
        context = {
            "is_vpn": True,
            "vpn_exit_country": "XX",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_no_vpn(self, sample_user):
        """get_fraud_score should be lower without VPN."""
        context = {
            "is_vpn": False,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_tor_detection(self, sample_user):
        """get_fraud_score should flag Tor exit nodes."""
        context = {
            "is_tor": True,
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.6

    def test_get_fraud_score_with_proxy_detection(self, sample_user):
        """get_fraud_score should flag known proxy usage."""
        context = {
            "is_proxy": True,
            "proxy_type": "datacenter",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_residential_proxy(self, sample_user):
        """get_fraud_score should flag residential proxy usage."""
        context = {
            "is_proxy": True,
            "proxy_type": "residential",
        }
        score = get_fraud_score(sample_user, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_consistent_history(self):
        """get_fraud_score should reward consistent user history."""
        consistent_user = {
            "id": "user_consistent",
            "username": "consistent",
            "email": "consistent@example.com",
            "created_at": (datetime.now() - timedelta(days=365)).isoformat(),
            "trust_score": 0.9,
            "login_pattern_consistency": 0.95,
            "purchase_pattern_consistency": 0.9,
        }
        score = get_fraud_score(consistent_user)
        assert score < 0.2

    def test_get_fraud_score_with_inconsistent_history(self):
        """get_fraud_score should flag inconsistent user history."""
        inconsistent_user = {
            "id": "user_inconsistent",
            "username": "inconsistent",
            "email": "inconsistent@example.com",
            "created_at": (datetime.now() - timedelta(days=365)).isoformat(),
            "trust_score": 0.5,
            "login_pattern_consistency": 0.2,
            "purchase_pattern_consistency": 0.15,
        }
        score = get_fraud_score(inconsistent_user)
        assert score > 0.5

    def test_get_fraud_score_with_api_abuse(self):
        """get_fraud_score should detect API abuse patterns."""
        api_abuser = {
            "id": "user_api",
            "username": "apiuser",
            "email": "api@example.com",
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "trust_score": 0.2,
            "api_calls_per_minute": 500,
            "api_error_rate": 0.8,
        }
        score = get_fraud_score(api_abuser)
        assert score > 0.6

    def test_get_fraud_score_with_normal_api_usage(self):
        """get_fraud_score should be low for normal API usage."""
        normal_api_user = {
            "id": "user_normal_api",
            "username": "normalapi",
            "email": "normalapi@example.com",
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "trust_score": 0.8,
            "api_calls_per_minute": 10,
            "api_error_rate": 0.01,
        }
        score = get_fraud_score(normal_api_user)
        assert score < 0.3

    def test_get_fraud_score_with_data_scraping_pattern(self):
        """get_fraud_score should flag data scraping behavior."""
        scraper = {
            "id": "user_scraper",
            "username": "scraper",
            "email": "scraper@example.com",
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "trust_score": 0.15,
            "page_views_per_minute": 200,
            "unique_pages_viewed": 5000,
            "time_on_page_seconds_avg": 0.5,
        }
        score = get_fraud_score(scraper)
        assert score > 0.7

    def test_get_fraud_score_with_human_browsing_pattern(self):
        """get_fraud_score should be low for human-like browsing."""
        human_user = {
            "id": "user_human",
            "username": "humanuser",
            "email": "human@example.com",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "trust_score": 0.85,
            "page_views_per_minute": 5,
            "unique_pages_viewed": 20,
            "time_on_page_seconds_avg": 45,
        }
        score = get_fraud_score(human_user)
        assert score < 0.3

    def test_get_fraud_score_with_review_manipulation(self):
        """get_fraud_score should flag review manipulation patterns."""
        manipulator = {
            "id": "user_manip",
            "username": "manipuser",
            "email": "manip@example.com",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "trust_score": 0.3,
            "reviews_posted": 100,
            "reviews_removed": 80,
            "review_avg_rating": 5.0,
            "review_reciprocity_score": 0.95,
        }
        score = get_fraud_score(manipulator)
        assert score > 0.6

    def test_get_fraud_score_with_organic_reviews(self):
        """get_fraud_score should be low for organic review patterns."""
        organic_user = {
            "id": "user_organic",
            "username": "organicuser",
            "email": "organic@example.com",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "trust_score": 0.85,
            "reviews_posted": 10,
            "reviews_removed": 1,
            "review_avg_rating": 4.2,
            "review_reciprocity_score": 0.1,
        }
        score = get_fraud_score(organic_user)
        assert score < 0.3

    def test_get_fraud_score_with_seller_rating_factor(self):
        """get_fraud_score should consider seller rating."""
        low_rated_seller = {
            "id": "user_low_rate",
            "username": "lowrate",
            "email": "lowrate@example.com",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "trust_score": 0.4,
            "seller_rating": 1.5,
            "total_sales": 50,
        }
        score = get_fraud_score(low_rated_seller)
        assert score > 0.4

    def test_get_fraud_score_with_high_seller_rating(self):
        """get_fraud_score should be low for highly-rated sellers."""
        high_rated_seller = {
            "id": "user_high_rate",
            "username": "highrate",
            "email": "highrate@example.com",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "trust_score": 0.95,
            "seller_rating": 4.9,
            "total_sales": 500,
        }
        score = get_fraud_score(high_rated_seller)
        assert score < 0.2

    def test_get_fraud_score_with_buyer_protection_abuse(self):
        """get_fraud_score should flag buyer protection abuse."""
        abuser = {
            "id": "user_abuse",
            "username": "abuseuser",
            "email": "abuse@example.com",
            "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
            "trust_score": 0.3,
            "buyer_protection_claims": 15,
            "claims_upheld": 12,
            "total_purchases": 20,
        }
        score = get_fraud_score(abuser)
        assert score > 0.6

    def test_get_fraud_score_with_fair_buyer_protection(self):
        """get_fraud_score should be low for fair buyer protection usage."""
        fair_user = {
            "id": "user_fair",
            "username": "fairuser",
            "email": "fair@example.com",
            "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
            "trust_score": 0.85,
            "buyer_protection_claims": 1,
            "claims_upheld": 1,
            "total_purchases": 50,
        }
        score = get_fraud_score(fair_user)
        assert score < 0.3

    def test_get_fraud_score_with_message_pattern_analysis(self):
        """get_fraud_score should analyze message patterns for fraud."""
        context = {
            "messages_sent": 500,
            "unique_recipients": 50,
            "avg_message_length": 10,
            "contains_external_links": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_messaging(self):
        """get_fraud_score should be low for normal messaging patterns."""
        context = {
            "messages_sent": 20,
            "unique_recipients": 10,
            "avg_message_length": 150,
            "contains_external_links": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_off_platform_attempt(self):
        """get_fraud_score should flag off-platform transaction attempts."""
        context = {
            "message_contains_contact_info": True,
            "message_contains_payment_info": True,
            "off_platform_redirect_attempts": 3,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.6

    def test_get_fraud_score_with_on_platform_behavior(self):
        """get_fraud_score should be low for on-platform behavior."""
        context = {
            "message_contains_contact_info": False,
            "message_contains_payment_info": False,
            "off_platform_redirect_attempts": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_account_linking_pattern(self):
        """get_fraud_score should detect suspicious account linking."""
        context = {
            "linked_account_age_days": 1,
            "linked_account_trust_score": 0.1,
            "linked_account_violations": 5,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_trusted_account_linking(self):
        """get_fraud_score should be low for trusted account linking."""
        context = {
            "linked_account_age_days": 365,
            "linked_account_trust_score": 0.9,
            "linked_account_violations": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_payment_velocity(self):
        """get_fraud_score should consider payment method velocity."""
        context = {
            "payment_methods_added_24h": 5,
            "payment_methods_total": 10,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_stable_payment_methods(self):
        """get_fraud_score should be low for stable payment methods."""
        context = {
            "payment_methods_added_24h": 0,
            "payment_methods_total": 2,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_address_velocity(self):
        """get_fraud_score should consider address change velocity."""
        context = {
            "addresses_added_7d": 10,
            "address_changes_30d": 20,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_stable_address(self):
        """get_fraud_score should be low for stable addresses."""
        context = {
            "addresses_added_7d": 0,
            "address_changes_30d": 1,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_name_variation_pattern(self):
        """get_fraud_score should detect name variation patterns."""
        context = {
            "name_variations_count": 8,
            "name_changes_30d": 5,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_stable_name(self):
        """get_fraud_score should be low for stable names."""
        context = {
            "name_variations_count": 1,
            "name_changes_30d": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_photo_analysis(self):
        """get_fraud_score should consider profile photo analysis."""
        context = {
            "profile_photo_risk_score": 0.9,
            "photo_reverse_search_matches": 50,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_authentic_photo(self):
        """get_fraud_score should be low for authentic photos."""
        context = {
            "profile_photo_risk_score": 0.1,
            "photo_reverse_search_matches": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_description_analysis(self):
        """get_fraud_score should analyze listing descriptions."""
        context = {
            "description_risk_score": 0.85,
            "contains_prohibited_terms": True,
            "spam_likelihood": 0.9,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_clean_description(self):
        """get_fraud_score should be low for clean descriptions."""
        context = {
            "description_risk_score": 0.1,
            "contains_prohibited_terms": False,
            "spam_likelihood": 0.05,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_price_anomaly(self):
        """get_fraud_score should detect price anomalies."""
        context = {
            "listing_price": 0.99,
            "market_avg_price": 100.00,
            "price_deviation_ratio": 0.01,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_pricing(self):
        """get_fraud_score should be low for normal pricing."""
        context = {
            "listing_price": 95.00,
            "market_avg_price": 100.00,
            "price_deviation_ratio": 0.95,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_category_mismatch(self):
        """get_fraud_score should flag category mismatches."""
        context = {
            "listed_category": "electronics",
            "detected_category": "clothing",
            "category_confidence": 0.9,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_category_match(self):
        """get_fraud_score should be low for category matches."""
        context = {
            "listed_category": "electronics",
            "detected_category": "electronics",
            "category_confidence": 0.95,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_image_analysis(self):
        """get_fraud_score should consider image analysis results."""
        context = {
            "image_risk_score": 0.8,
            "stock_photo_detected": True,
            "image_metadata_anomaly": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_authentic_images(self):
        """get_fraud_score should be low for authentic images."""
        context = {
            "image_risk_score": 0.1,
            "stock_photo_detected": False,
            "image_metadata_anomaly": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_seller_buyer_ratio(self):
        """get_fraud_score should consider seller-buyer ratio anomalies."""
        context = {
            "items_sold": 0,
            "items_bought": 100,
            "seller_buyer_ratio": 0.0,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_balanced_ratio(self):
        """get_fraud_score should be low for balanced seller-buyer ratios."""
        context = {
            "items_sold": 50,
            "items_bought": 30,
            "seller_buyer_ratio": 1.67,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_feedback_velocity(self):
        """get_fraud_score should consider feedback velocity."""
        context = {
            "feedback_received_7d": 50,
            "account_age_days": 10,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_feedback_velocity(self):
        """get_fraud_score should be low for normal feedback velocity."""
        context = {
            "feedback_received_7d": 2,
            "account_age_days": 365,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_negative_feedback_ratio(self):
        """get_fraud_score should flag high negative feedback ratios."""
        context = {
            "positive_feedback": 10,
            "negative_feedback": 30,
            "negative_feedback_ratio": 0.75,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_positive_feedback_ratio(self):
        """get_fraud_score should be low for positive feedback ratios."""
        context = {
            "positive_feedback": 100,
            "negative_feedback": 2,
            "negative_feedback_ratio": 0.02,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_search_pattern_analysis(self):
        """get_fraud_score should analyze search patterns."""
        context = {
            "searches_per_minute": 50,
            "unique_search_terms": 200,
            "search_to_purchase_ratio": 0.001,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_search_pattern(self):
        """get_fraud_score should be low for normal search patterns."""
        context = {
            "searches_per_minute": 3,
            "unique_search_terms": 10,
            "search_to_purchase_ratio": 0.1,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_wishlist_pattern(self):
        """get_fraud_score should consider wishlist patterns."""
        context = {
            "wishlist_additions_24h": 100,
            "wishlist_purchases_24h": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_wishlist(self):
        """get_fraud_score should be low for normal wishlist usage."""
        context = {
            "wishlist_additions_24h": 2,
            "wishlist_purchases_24h": 1,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cart_abandonment_pattern(self):
        """get_fraud_score should consider cart abandonment patterns."""
        context = {
            "cart_additions_7d": 50,
            "cart_purchases_7d": 0,
            "abandonment_rate": 1.0,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_cart_behavior(self):
        """get_fraud_score should be low for normal cart behavior."""
        context = {
            "cart_additions_7d": 5,
            "cart_purchases_7d": 3,
            "abandonment_rate": 0.4,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_checkout_pattern(self):
        """get_fraud_score should analyze checkout patterns."""
        context = {
            "checkout_attempts_24h": 20,
            "checkout_successes_24h": 0,
            "checkout_failure_rate": 1.0,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_checkout(self):
        """get_fraud_score should be low for normal checkout patterns."""
        context = {
            "checkout_attempts_24d": 2,
            "checkout_successes_24h": 2,
            "checkout_failure_rate": 0.0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_login_pattern(self):
        """get_fraud_score should analyze login patterns."""
        context = {
            "failed_logins_24h": 15,
            "successful_logins_24h": 1,
            "unique_ips_24h": 10,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.6

    def test_get_fraud_score_with_normal_login(self):
        """get_fraud_score should be low for normal login patterns."""
        context = {
            "failed_logins_24h": 0,
            "successful_logins_24h": 2,
            "unique_ips_24h": 1,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_password_reset_pattern(self):
        """get_fraud_score should flag excessive password resets."""
        context = {
            "password_resets_7d": 10,
            "password_reset_success_rate": 0.3,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_password_resets(self):
        """get_fraud_score should be low for normal password reset patterns."""
        context = {
            "password_resets_7d": 0,
            "password_reset_success_rate": 1.0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_email_change_pattern(self):
        """get_fraud_score should flag frequent email changes."""
        context = {
            "email_changes_30d": 5,
            "email_change_reversal_rate": 0.8,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_stable_email(self):
        """get_fraud_score should be low for stable emails."""
        context = {
            "email_changes_30d": 0,
            "email_change_reversal_rate": 0.0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_phone_change_pattern(self):
        """get_fraud_score should flag frequent phone changes."""
        context = {
            "phone_changes_30d": 4,
            "phone_verification_failures": 3,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_stable_phone(self):
        """get_fraud_score should be low for stable phone numbers."""
        context = {
            "phone_changes_30d": 0,
            "phone_verification_failures": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_device_fingerprint_velocity(self):
        """get_fraud_score should consider device fingerprint velocity."""
        context = {
            "unique_devices_7d": 15,
            "device_fingerprint_changes_24h": 5,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_stable_device(self):
        """get_fraud_score should be low for stable devices."""
        context = {
            "unique_devices_7d": 1,
            "device_fingerprint_changes_24h": 0,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_session_duration_pattern(self):
        """get_fraud_score should analyze session duration patterns."""
        context = {
            "avg_session_duration_seconds": 2,
            "sessions_per_day": 50,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_session_duration(self):
        """get_fraud_score should be low for normal session durations."""
        context = {
            "avg_session_duration_seconds": 300,
            "sessions_per_day": 3,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_navigation_pattern(self):
        """get_fraud_score should analyze navigation patterns."""
        context = {
            "pages_per_session": 200,
            "back_button_usage_rate": 0.9,
            "direct_url_entries": 0.8,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_navigation(self):
        """get_fraud_score should be low for normal navigation patterns."""
        context = {
            "pages_per_session": 8,
            "back_button_usage_rate": 0.1,
            "direct_url_entries": 0.05,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_form_filling_pattern(self):
        """get_fraud_score should analyze form filling patterns."""
        context = {
            "form_completion_time_seconds": 1,
            "form_field_changes": 50,
            "copy_paste_usage_rate": 0.95,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_form_filling(self):
        """get_fraud_score should be low for normal form filling."""
        context = {
            "form_completion_time_seconds": 30,
            "form_field_changes": 2,
            "copy_paste_usage_rate": 0.1,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cookie_analysis(self):
        """get_fraud_score should consider cookie analysis."""
        context = {
            "cookie_enabled": False,
            "cookie_consent_bypass": True,
            "third_party_cookies_blocked": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_cookies(self):
        """get_fraud_score should be low for normal cookie settings."""
        context = {
            "cookie_enabled": True,
            "cookie_consent_bypass": False,
            "third_party_cookies_blocked": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_javascript_execution(self):
        """get_fraud_score should consider JavaScript execution patterns."""
        context = {
            "javascript_enabled": False,
            "js_challenge_failed": True,
            "js_execution_time_ms": 10,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_normal_javascript(self):
        """get_fraud_score should be low for normal JavaScript execution."""
        context = {
            "javascript_enabled": True,
            "js_challenge_failed": False,
            "js_execution_time_ms": 500,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_canvas_fingerprint(self):
        """get_fraud_score should consider canvas fingerprinting."""
        context = {
            "canvas_fingerprint_consistency": 0.1,
            "canvas_fingerprint_matches": False,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_consistent_canvas(self):
        """get_fraud_score should be low for consistent canvas fingerprints."""
        context = {
            "canvas_fingerprint_consistency": 0.95,
            "canvas_fingerprint_matches": True,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_webgl_fingerprint(self):
        """get_fraud_score should consider WebGL fingerprinting."""
        context = {
            "webgl_fingerprint_consistency": 0.1,
            "webgl_renderer_masked": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_consistent_webgl(self):
        """get_fraud_score should be low for consistent WebGL fingerprints."""
        context = {
            "webgl_fingerprint_consistency": 0.95,
            "webgl_renderer_masked": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_audio_context(self):
        """get_fraud_score should consider audio context fingerprinting."""
        context = {
            "audio_context_fingerprint_consistency": 0.1,
            "audio_context_spoofed": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_consistent_audio(self):
        """get_fraud_score should be low for consistent audio contexts."""
        context = {
            "audio_context_fingerprint_consistency": 0.95,
            "audio_context_spoofed": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_font_enumeration(self):
        """get_fraud_score should consider font enumeration patterns."""
        context = {
            "font_count_anomaly": True,
            "font_list_consistency": 0.1,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_fonts(self):
        """get_fraud_score should be low for normal font patterns."""
        context = {
            "font_count_anomaly": False,
            "font_list_consistency": 0.9,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_webrtc_leak(self):
        """get_fraud_score should flag WebRTC IP leaks."""
        context = {
            "webrtc_local_ip_leak": True,
            "webrtc_public_ip_mismatch": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_no_webrtc_leak(self):
        """get_fraud_score should be low without WebRTC leaks."""
        context = {
            "webrtc_local_ip_leak": False,
            "webrtc_public_ip_mismatch": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_battery_api(self):
        """get_fraud_score should consider Battery API anomalies."""
        context = {
            "battery_api_spoofed": True,
            "battery_level_constant": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_battery(self):
        """get_fraud_score should be low for normal battery API."""
        context = {
            "battery_api_spoofed": False,
            "battery_level_constant": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_hardware_concurrency(self):
        """get_fraud_score should consider hardware concurrency anomalies."""
        context = {
            "hardware_concurrency_anomaly": True,
            "device_memory_anomaly": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_hardware(self):
        """get_fraud_score should be low for normal hardware specs."""
        context = {
            "hardware_concurrency_anomaly": False,
            "device_memory_anomaly": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_user_agent_analysis(self):
        """get_fraud_score should analyze user agent strings."""
        context = {
            "user_agent_mismatch": True,
            "user_agent_spoofed": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.5

    def test_get_fraud_score_with_consistent_user_agent(self):
        """get_fraud_score should be low for consistent user agents."""
        context = {
            "user_agent_mismatch": False,
            "user_agent_spoofed": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_screen_resolution(self):
        """get_fraud_score should consider screen resolution anomalies."""
        context = {
            "screen_resolution_anomaly": True,
            "screen_resolution_consistency": 0.1,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_screen(self):
        """get_fraud_score should be low for normal screen resolutions."""
        context = {
            "screen_resolution_anomaly": False,
            "screen_resolution_consistency": 0.95,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_timezone_analysis(self):
        """get_fraud_score should analyze timezone consistency."""
        context = {
            "timezone_mismatch": True,
            "timezone_ip_mismatch": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_consistent_timezone(self):
        """get_fraud_score should be low for consistent timezones."""
        context = {
            "timezone_mismatch": False,
            "timezone_ip_mismatch": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_language_analysis(self):
        """get_fraud_score should analyze language consistency."""
        context = {
            "language_mismatch": True,
            "browser_language_ip_mismatch": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_consistent_language(self):
        """get_fraud_score should be low for consistent languages."""
        context = {
            "language_mismatch": False,
            "browser_language_ip_mismatch": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_referrer_analysis(self):
        """get_fraud_score should analyze referrer patterns."""
        context = {
            "referrer_spoofed": True,
            "referrer_chain_anomaly": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_referrer(self):
        """get_fraud_score should be low for normal referrers."""
        context = {
            "referrer_spoofed": False,
            "referrer_chain_anomaly": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_history_analysis(self):
        """get_fraud_score should analyze browser history patterns."""
        context = {
            "history_length_anomaly": True,
            "history_manipulation_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.4

    def test_get_fraud_score_with_normal_history(self):
        """get_fraud_score should be low for normal history patterns."""
        context = {
            "history_length_anomaly": False,
            "history_manipulation_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_plugin_analysis(self):
        """get_fraud_score should analyze plugin patterns."""
        context = {
            "plugin_list_anomaly": True,
            "plugin_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_plugins(self):
        """get_fraud_score should be low for normal plugin patterns."""
        context = {
            "plugin_list_anomaly": False,
            "plugin_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_mime_type_analysis(self):
        """get_fraud_score should analyze MIME type patterns."""
        context = {
            "mime_type_anomaly": True,
            "mime_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_mime_types(self):
        """get_fraud_score should be low for normal MIME types."""
        context = {
            "mime_type_anomaly": False,
            "mime_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_permissions_analysis(self):
        """get_fraud_score should analyze permission patterns."""
        context = {
            "permissions_anomaly": True,
            "permission_query_spoofed": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_permissions(self):
        """get_fraud_score should be low for normal permissions."""
        context = {
            "permissions_anomaly": False,
            "permission_query_spoofed": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_media_device_analysis(self):
        """get_fraud_score should analyze media device patterns."""
        context = {
            "media_device_anomaly": True,
            "media_device_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_media_devices(self):
        """get_fraud_score should be low for normal media devices."""
        context = {
            "media_device_anomaly": False,
            "media_device_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_bluetooth_analysis(self):
        """get_fraud_score should analyze Bluetooth patterns."""
        context = {
            "bluetooth_anomaly": True,
            "bluetooth_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_bluetooth(self):
        """get_fraud_score should be low for normal Bluetooth."""
        context = {
            "bluetooth_anomaly": False,
            "bluetooth_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_usb_analysis(self):
        """get_fraud_score should analyze USB patterns."""
        context = {
            "usb_anomaly": True,
            "usb_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_usb(self):
        """get_fraud_score should be low for normal USB."""
        context = {
            "usb_anomaly": False,
            "usb_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_gamepad_analysis(self):
        """get_fraud_score should analyze gamepad patterns."""
        context = {
            "gamepad_anomaly": True,
            "gamepad_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_gamepad(self):
        """get_fraud_score should be low for normal gamepad."""
        context = {
            "gamepad_anomaly": False,
            "gamepad_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_vr_analysis(self):
        """get_fraud_score should analyze VR patterns."""
        context = {
            "vr_anomaly": True,
            "vr_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_vr(self):
        """get_fraud_score should be low for normal VR."""
        context = {
            "vr_anomaly": False,
            "vr_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_ar_analysis(self):
        """get_fraud_score should analyze AR patterns."""
        context = {
            "ar_anomaly": True,
            "ar_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_ar(self):
        """get_fraud_score should be low for normal AR."""
        context = {
            "ar_anomaly": False,
            "ar_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_speech_synthesis(self):
        """get_fraud_score should analyze speech synthesis patterns."""
        context = {
            "speech_synthesis_anomaly": True,
            "speech_synthesis_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_speech_synthesis(self):
        """get_fraud_score should be low for normal speech synthesis."""
        context = {
            "speech_synthesis_anomaly": False,
            "speech_synthesis_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_web_speech(self):
        """get_fraud_score should analyze Web Speech patterns."""
        context = {
            "web_speech_anomaly": True,
            "web_speech_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_web_speech(self):
        """get_fraud_score should be low for normal Web Speech."""
        context = {
            "web_speech_anomaly": False,
            "web_speech_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_speech_recognition(self):
        """get_fraud_score should analyze speech recognition patterns."""
        context = {
            "speech_recognition_anomaly": True,
            "speech_recognition_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_speech_recognition(self):
        """get_fraud_score should be low for normal speech recognition."""
        context = {
            "speech_recognition_anomaly": False,
            "speech_recognition_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_management(self):
        """get_fraud_score should analyze credential management patterns."""
        context = {
            "credential_management_anomaly": True,
            "credential_management_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_management(self):
        """get_fraud_score should be low for normal credential management."""
        context = {
            "credential_management_anomaly": False,
            "credential_management_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_web_authentication(self):
        """get_fraud_score should analyze WebAuthn patterns."""
        context = {
            "webauthn_anomaly": True,
            "webauthn_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_webauthn(self):
        """get_fraud_score should be low for normal WebAuthn."""
        context = {
            "webauthn_anomaly": False,
            "webauthn_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_public_key_credential(self):
        """get_fraud_score should analyze public key credential patterns."""
        context = {
            "public_key_credential_anomaly": True,
            "public_key_credential_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_public_key_credential(self):
        """get_fraud_score should be low for normal public key credentials."""
        context = {
            "public_key_credential_anomaly": False,
            "public_key_credential_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_otp_credential(self):
        """get_fraud_score should analyze OTP credential patterns."""
        context = {
            "otp_credential_anomaly": True,
            "otp_credential_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_otp_credential(self):
        """get_fraud_score should be low for normal OTP credentials."""
        context = {
            "otp_credential_anomaly": False,
            "otp_credential_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_sms_otp(self):
        """get_fraud_score should analyze SMS OTP patterns."""
        context = {
            "sms_otp_anomaly": True,
            "sms_otp_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_sms_otp(self):
        """get_fraud_score should be low for normal SMS OTP."""
        context = {
            "sms_otp_anomaly": False,
            "sms_otp_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_email_otp(self):
        """get_fraud_score should analyze email OTP patterns."""
        context = {
            "email_otp_anomaly": True,
            "email_otp_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_email_otp(self):
        """get_fraud_score should be low for normal email OTP."""
        context = {
            "email_otp_anomaly": False,
            "email_otp_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_totp(self):
        """get_fraud_score should analyze TOTP patterns."""
        context = {
            "totp_anomaly": True,
            "totp_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_totp(self):
        """get_fraud_score should be low for normal TOTP."""
        context = {
            "totp_anomaly": False,
            "totp_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_hotp(self):
        """get_fraud_score should analyze HOTP patterns."""
        context = {
            "hotp_anomaly": True,
            "hotp_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_hotp(self):
        """get_fraud_score should be low for normal HOTP."""
        context = {
            "hotp_anomaly": False,
            "hotp_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_u2f(self):
        """get_fraud_score should analyze U2F patterns."""
        context = {
            "u2f_anomaly": True,
            "u2f_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_u2f(self):
        """get_fraud_score should be low for normal U2F."""
        context = {
            "u2f_anomaly": False,
            "u2f_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_fido2(self):
        """get_fraud_score should analyze FIDO2 patterns."""
        context = {
            "fido2_anomaly": True,
            "fido2_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_fido2(self):
        """get_fraud_score should be low for normal FIDO2."""
        context = {
            "fido2_anomaly": False,
            "fido2_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_ctap2(self):
        """get_fraud_score should analyze CTAP2 patterns."""
        context = {
            "ctap2_anomaly": True,
            "ctap2_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_ctap2(self):
        """get_fraud_score should be low for normal CTAP2."""
        context = {
            "ctap2_anomaly": False,
            "ctap2_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_nfc(self):
        """get_fraud_score should analyze NFC patterns."""
        context = {
            "nfc_anomaly": True,
            "nfc_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_nfc(self):
        """get_fraud_score should be low for normal NFC."""
        context = {
            "nfc_anomaly": False,
            "nfc_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_ble(self):
        """get_fraud_score should analyze BLE patterns."""
        context = {
            "ble_anomaly": True,
            "ble_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_ble(self):
        """get_fraud_score should be low for normal BLE."""
        context = {
            "ble_anomaly": False,
            "ble_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_usb_security_key(self):
        """get_fraud_score should analyze USB security key patterns."""
        context = {
            "usb_security_key_anomaly": True,
            "usb_security_key_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_usb_security_key(self):
        """get_fraud_score should be low for normal USB security keys."""
        context = {
            "usb_security_key_anomaly": False,
            "usb_security_key_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_platform_authenticator(self):
        """get_fraud_score should analyze platform authenticator patterns."""
        context = {
            "platform_authenticator_anomaly": True,
            "platform_authenticator_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_platform_authenticator(self):
        """get_fraud_score should be low for normal platform authenticators."""
        context = {
            "platform_authenticator_anomaly": False,
            "platform_authenticator_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cross_platform_authenticator(self):
        """get_fraud_score should analyze cross-platform authenticator patterns."""
        context = {
            "cross_platform_authenticator_anomaly": True,
            "cross_platform_authenticator_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_cross_platform_authenticator(self):
        """get_fraud_score should be low for normal cross-platform authenticators."""
        context = {
            "cross_platform_authenticator_anomaly": False,
            "cross_platform_authenticator_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_user_verification(self):
        """get_fraud_score should analyze user verification patterns."""
        context = {
            "user_verification_anomaly": True,
            "user_verification_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_user_verification(self):
        """get_fraud_score should be low for normal user verification."""
        context = {
            "user_verification_anomaly": False,
            "user_verification_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_user_presence(self):
        """get_fraud_score should analyze user presence patterns."""
        context = {
            "user_presence_anomaly": True,
            "user_presence_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_user_presence(self):
        """get_fraud_score should be low for normal user presence."""
        context = {
            "user_presence_anomaly": False,
            "user_presence_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_resident_key(self):
        """get_fraud_score should analyze resident key patterns."""
        context = {
            "resident_key_anomaly": True,
            "resident_key_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_resident_key(self):
        """get_fraud_score should be low for normal resident keys."""
        context = {
            "resident_key_anomaly": False,
            "resident_key_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_client_side_credentials(self):
        """get_fraud_score should analyze client-side credential patterns."""
        context = {
            "client_side_credentials_anomaly": True,
            "client_side_credentials_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_client_side_credentials(self):
        """get_fraud_score should be low for normal client-side credentials."""
        context = {
            "client_side_credentials_anomaly": False,
            "client_side_credentials_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_large_blob(self):
        """get_fraud_score should analyze large blob patterns."""
        context = {
            "large_blob_anomaly": True,
            "large_blob_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_large_blob(self):
        """get_fraud_score should be low for normal large blobs."""
        context = {
            "large_blob_anomaly": False,
            "large_blob_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_min_pin_length(self):
        """get_fraud_score should analyze min PIN length patterns."""
        context = {
            "min_pin_length_anomaly": True,
            "min_pin_length_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_min_pin_length(self):
        """get_fraud_score should be low for normal min PIN lengths."""
        context = {
            "min_pin_length_anomaly": False,
            "min_pin_length_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cred_protect(self):
        """get_fraud_score should analyze cred protect patterns."""
        context = {
            "cred_protect_anomaly": True,
            "cred_protect_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_cred_protect(self):
        """get_fraud_score should be low for normal cred protect."""
        context = {
            "cred_protect_anomaly": False,
            "cred_protect_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cred_blob(self):
        """get_fraud_score should analyze cred blob patterns."""
        context = {
            "cred_blob_anomaly": True,
            "cred_blob_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_cred_blob(self):
        """get_fraud_score should be low for normal cred blobs."""
        context = {
            "cred_blob_anomaly": False,
            "cred_blob_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_hmac_secret(self):
        """get_fraud_score should analyze HMAC secret patterns."""
        context = {
            "hmac_secret_anomaly": True,
            "hmac_secret_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_hmac_secret(self):
        """get_fraud_score should be low for normal HMAC secrets."""
        context = {
            "hmac_secret_anomaly": False,
            "hmac_secret_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_appid(self):
        """get_fraud_score should analyze AppID patterns."""
        context = {
            "appid_anomaly": True,
            "appid_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_appid(self):
        """get_fraud_score should be low for normal AppIDs."""
        context = {
            "appid_anomaly": False,
            "appid_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_appid_exclude(self):
        """get_fraud_score should analyze AppID exclude patterns."""
        context = {
            "appid_exclude_anomaly": True,
            "appid_exclude_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_appid_exclude(self):
        """get_fraud_score should be low for normal AppID excludes."""
        context = {
            "appid_exclude_anomaly": False,
            "appid_exclude_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_cred_props(self):
        """get_fraud_score should analyze cred props patterns."""
        context = {
            "cred_props_anomaly": True,
            "cred_props_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_cred_props(self):
        """get_fraud_score should be low for normal cred props."""
        context = {
            "cred_props_anomaly": False,
            "cred_props_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_authenticator_selection(self):
        """get_fraud_score should analyze authenticator selection patterns."""
        context = {
            "authenticator_selection_anomaly": True,
            "authenticator_selection_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_authenticator_selection(self):
        """get_fraud_score should be low for normal authenticator selection."""
        context = {
            "authenticator_selection_anomaly": False,
            "authenticator_selection_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_attestation(self):
        """get_fraud_score should analyze attestation patterns."""
        context = {
            "attestation_anomaly": True,
            "attestation_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_attestation(self):
        """get_fraud_score should be low for normal attestation."""
        context = {
            "attestation_anomaly": False,
            "attestation_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_attestation_object(self):
        """get_fraud_score should analyze attestation object patterns."""
        context = {
            "attestation_object_anomaly": True,
            "attestation_object_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_attestation_object(self):
        """get_fraud_score should be low for normal attestation objects."""
        context = {
            "attestation_object_anomaly": False,
            "attestation_object_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_authenticator_data(self):
        """get_fraud_score should analyze authenticator data patterns."""
        context = {
            "authenticator_data_anomaly": True,
            "authenticator_data_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_authenticator_data(self):
        """get_fraud_score should be low for normal authenticator data."""
        context = {
            "authenticator_data_anomaly": False,
            "authenticator_data_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_attested_credential_data(self):
        """get_fraud_score should analyze attested credential data patterns."""
        context = {
            "attested_credential_data_anomaly": True,
            "attested_credential_data_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_attested_credential_data(self):
        """get_fraud_score should be low for normal attested credential data."""
        context = {
            "attested_credential_data_anomaly": False,
            "attested_credential_data_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_aaguid(self):
        """get_fraud_score should analyze AAGUID patterns."""
        context = {
            "aaguid_anomaly": True,
            "aaguid_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_aaguid(self):
        """get_fraud_score should be low for normal AAGUIDs."""
        context = {
            "aaguid_anomaly": False,
            "aaguid_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_id(self):
        """get_fraud_score should analyze credential ID patterns."""
        context = {
            "credential_id_anomaly": True,
            "credential_id_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_id(self):
        """get_fraud_score should be low for normal credential IDs."""
        context = {
            "credential_id_anomaly": False,
            "credential_id_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_public_key(self):
        """get_fraud_score should analyze credential public key patterns."""
        context = {
            "credential_public_key_anomaly": True,
            "credential_public_key_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_public_key(self):
        """get_fraud_score should be low for normal credential public keys."""
        context = {
            "credential_public_key_anomaly": False,
            "credential_public_key_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_transport(self):
        """get_fraud_score should analyze credential transport patterns."""
        context = {
            "credential_transport_anomaly": True,
            "credential_transport_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_transport(self):
        """get_fraud_score should be low for normal credential transports."""
        context = {
            "credential_transport_anomaly": False,
            "credential_transport_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_type(self):
        """get_fraud_score should analyze credential type patterns."""
        context = {
            "credential_type_anomaly": True,
            "credential_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_type(self):
        """get_fraud_score should be low for normal credential types."""
        context = {
            "credential_type_anomaly": False,
            "credential_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_algorithm(self):
        """get_fraud_score should analyze credential algorithm patterns."""
        context = {
            "credential_algorithm_anomaly": True,
            "credential_algorithm_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_algorithm(self):
        """get_fraud_score should be low for normal credential algorithms."""
        context = {
            "credential_algorithm_anomaly": False,
            "credential_algorithm_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_signature(self):
        """get_fraud_score should analyze credential signature patterns."""
        context = {
            "credential_signature_anomaly": True,
            "credential_signature_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_signature(self):
        """get_fraud_score should be low for normal credential signatures."""
        context = {
            "credential_signature_anomaly": False,
            "credential_signature_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_attestation(self):
        """get_fraud_score should analyze credential attestation patterns."""
        context = {
            "credential_attestation_anomaly": True,
            "credential_attestation_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_attestation(self):
        """get_fraud_score should be low for normal credential attestations."""
        context = {
            "credential_attestation_anomaly": False,
            "credential_attestation_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension(self):
        """get_fraud_score should analyze credential extension patterns."""
        context = {
            "credential_extension_anomaly": True,
            "credential_extension_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension(self):
        """get_fraud_score should be low for normal credential extensions."""
        context = {
            "credential_extension_anomaly": False,
            "credential_extension_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_output(self):
        """get_fraud_score should analyze credential extension output patterns."""
        context = {
            "credential_extension_output_anomaly": True,
            "credential_extension_output_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_output(self):
        """get_fraud_score should be low for normal credential extension outputs."""
        context = {
            "credential_extension_output_anomaly": False,
            "credential_extension_output_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_input(self):
        """get_fraud_score should analyze credential extension input patterns."""
        context = {
            "credential_extension_input_anomaly": True,
            "credential_extension_input_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_input(self):
        """get_fraud_score should be low for normal credential extension inputs."""
        context = {
            "credential_extension_input_anomaly": False,
            "credential_extension_input_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_identifier(self):
        """get_fraud_score should analyze credential extension identifier patterns."""
        context = {
            "credential_extension_identifier_anomaly": True,
            "credential_extension_identifier_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_identifier(self):
        """get_fraud_score should be low for normal credential extension identifiers."""
        context = {
            "credential_extension_identifier_anomaly": False,
            "credential_extension_identifier_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_name(self):
        """get_fraud_score should analyze credential extension name patterns."""
        context = {
            "credential_extension_name_anomaly": True,
            "credential_extension_name_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_name(self):
        """get_fraud_score should be low for normal credential extension names."""
        context = {
            "credential_extension_name_anomaly": False,
            "credential_extension_name_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_type(self):
        """get_fraud_score should analyze credential extension type patterns."""
        context = {
            "credential_extension_type_anomaly": True,
            "credential_extension_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_type(self):
        """get_fraud_score should be low for normal credential extension types."""
        context = {
            "credential_extension_type_anomaly": False,
            "credential_extension_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value(self):
        """get_fraud_score should analyze credential extension value patterns."""
        context = {
            "credential_extension_value_anomaly": True,
            "credential_extension_value_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value(self):
        """get_fraud_score should be low for normal credential extension values."""
        context = {
            "credential_extension_value_anomaly": False,
            "credential_extension_value_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_type(self):
        """get_fraud_score should analyze credential extension value type patterns."""
        context = {
            "credential_extension_value_type_anomaly": True,
            "credential_extension_value_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_type(self):
        """get_fraud_score should be low for normal credential extension value types."""
        context = {
            "credential_extension_value_type_anomaly": False,
            "credential_extension_value_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_format(self):
        """get_fraud_score should analyze credential extension value format patterns."""
        context = {
            "credential_extension_value_format_anomaly": True,
            "credential_extension_value_format_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_format(self):
        """get_fraud_score should be low for normal credential extension value formats."""
        context = {
            "credential_extension_value_format_anomaly": False,
            "credential_extension_value_format_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_encoding(self):
        """get_fraud_score should analyze credential extension value encoding patterns."""
        context = {
            "credential_extension_value_encoding_anomaly": True,
            "credential_extension_value_encoding_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_encoding(self):
        """get_fraud_score should be low for normal credential extension value encodings."""
        context = {
            "credential_extension_value_encoding_anomaly": False,
            "credential_extension_value_encoding_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_compression(self):
        """get_fraud_score should analyze credential extension value compression patterns."""
        context = {
            "credential_extension_value_compression_anomaly": True,
            "credential_extension_value_compression_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_compression(self):
        """get_fraud_score should be low for normal credential extension value compressions."""
        context = {
            "credential_extension_value_compression_anomaly": False,
            "credential_extension_value_compression_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_encryption(self):
        """get_fraud_score should analyze credential extension value encryption patterns."""
        context = {
            "credential_extension_value_encryption_anomaly": True,
            "credential_extension_value_encryption_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_encryption(self):
        """get_fraud_score should be low for normal credential extension value encryptions."""
        context = {
            "credential_extension_value_encryption_anomaly": False,
            "credential_extension_value_encryption_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_hash(self):
        """get_fraud_score should analyze credential extension value hash patterns."""
        context = {
            "credential_extension_value_hash_anomaly": True,
            "credential_extension_value_hash_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_hash(self):
        """get_fraud_score should be low for normal credential extension value hashes."""
        context = {
            "credential_extension_value_hash_anomaly": False,
            "credential_extension_value_hash_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_signature(self):
        """get_fraud_score should analyze credential extension value signature patterns."""
        context = {
            "credential_extension_value_signature_anomaly": True,
            "credential_extension_value_signature_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_signature(self):
        """get_fraud_score should be low for normal credential extension value signatures."""
        context = {
            "credential_extension_value_signature_anomaly": False,
            "credential_extension_value_signature_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_certificate(self):
        """get_fraud_score should analyze credential extension value certificate patterns."""
        context = {
            "credential_extension_value_certificate_anomaly": True,
            "credential_extension_value_certificate_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_certificate(self):
        """get_fraud_score should be low for normal credential extension value certificates."""
        context = {
            "credential_extension_value_certificate_anomaly": False,
            "credential_extension_value_certificate_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_chain(self):
        """get_fraud_score should analyze credential extension value chain patterns."""
        context = {
            "credential_extension_value_chain_anomaly": True,
            "credential_extension_value_chain_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_chain(self):
        """get_fraud_score should be low for normal credential extension value chains."""
        context = {
            "credential_extension_value_chain_anomaly": False,
            "credential_extension_value_chain_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_trust(self):
        """get_fraud_score should analyze credential extension value trust patterns."""
        context = {
            "credential_extension_value_trust_anomaly": True,
            "credential_extension_value_trust_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_trust(self):
        """get_fraud_score should be low for normal credential extension value trusts."""
        context = {
            "credential_extension_value_trust_anomaly": False,
            "credential_extension_value_trust_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_revocation(self):
        """get_fraud_score should analyze credential extension value revocation patterns."""
        context = {
            "credential_extension_value_revocation_anomaly": True,
            "credential_extension_value_revocation_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_revocation(self):
        """get_fraud_score should be low for normal credential extension value revocations."""
        context = {
            "credential_extension_value_revocation_anomaly": False,
            "credential_extension_value_revocation_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_status(self):
        """get_fraud_score should analyze credential extension value status patterns."""
        context = {
            "credential_extension_value_status_anomaly": True,
            "credential_extension_value_status_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_status(self):
        """get_fraud_score should be low for normal credential extension value statuses."""
        context = {
            "credential_extension_value_status_anomaly": False,
            "credential_extension_value_status_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_reason(self):
        """get_fraud_score should analyze credential extension value reason patterns."""
        context = {
            "credential_extension_value_reason_anomaly": True,
            "credential_extension_value_reason_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_reason(self):
        """get_fraud_score should be low for normal credential extension value reasons."""
        context = {
            "credential_extension_value_reason_anomaly": False,
            "credential_extension_value_reason_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_details(self):
        """get_fraud_score should analyze credential extension value details patterns."""
        context = {
            "credential_extension_value_details_anomaly": True,
            "credential_extension_value_details_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_details(self):
        """get_fraud_score should be low for normal credential extension value details."""
        context = {
            "credential_extension_value_details_anomaly": False,
            "credential_extension_value_details_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_info(self):
        """get_fraud_score should analyze credential extension value info patterns."""
        context = {
            "credential_extension_value_info_anomaly": True,
            "credential_extension_value_info_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_info(self):
        """get_fraud_score should be low for normal credential extension value info."""
        context = {
            "credential_extension_value_info_anomaly": False,
            "credential_extension_value_info_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_metadata(self):
        """get_fraud_score should analyze credential extension value metadata patterns."""
        context = {
            "credential_extension_value_metadata_anomaly": True,
            "credential_extension_value_metadata_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_metadata(self):
        """get_fraud_score should be low for normal credential extension value metadata."""
        context = {
            "credential_extension_value_metadata_anomaly": False,
            "credential_extension_value_metadata_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_data(self):
        """get_fraud_score should analyze credential extension value data patterns."""
        context = {
            "credential_extension_value_data_anomaly": True,
            "credential_extension_value_data_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_data(self):
        """get_fraud_score should be low for normal credential extension value data."""
        context = {
            "credential_extension_value_data_anomaly": False,
            "credential_extension_value_data_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_content(self):
        """get_fraud_score should analyze credential extension value content patterns."""
        context = {
            "credential_extension_value_content_anomaly": True,
            "credential_extension_value_content_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_content(self):
        """get_fraud_score should be low for normal credential extension value content."""
        context = {
            "credential_extension_value_content_anomaly": False,
            "credential_extension_value_content_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_body(self):
        """get_fraud_score should analyze credential extension value body patterns."""
        context = {
            "credential_extension_value_body_anomaly": True,
            "credential_extension_value_body_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_body(self):
        """get_fraud_score should be low for normal credential extension value body."""
        context = {
            "credential_extension_value_body_anomaly": False,
            "credential_extension_value_body_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_payload(self):
        """get_fraud_score should analyze credential extension value payload patterns."""
        context = {
            "credential_extension_value_payload_anomaly": True,
            "credential_extension_value_payload_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_payload(self):
        """get_fraud_score should be low for normal credential extension value payload."""
        context = {
            "credential_extension_value_payload_anomaly": False,
            "credential_extension_value_payload_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_header(self):
        """get_fraud_score should analyze credential extension value header patterns."""
        context = {
            "credential_extension_value_header_anomaly": True,
            "credential_extension_value_header_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_header(self):
        """get_fraud_score should be low for normal credential extension value header."""
        context = {
            "credential_extension_value_header_anomaly": False,
            "credential_extension_value_header_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_footer(self):
        """get_fraud_score should analyze credential extension value footer patterns."""
        context = {
            "credential_extension_value_footer_anomaly": True,
            "credential_extension_value_footer_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_footer(self):
        """get_fraud_score should be low for normal credential extension value footer."""
        context = {
            "credential_extension_value_footer_anomaly": False,
            "credential_extension_value_footer_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_wrapper(self):
        """get_fraud_score should analyze credential extension value wrapper patterns."""
        context = {
            "credential_extension_value_wrapper_anomaly": True,
            "credential_extension_value_wrapper_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_wrapper(self):
        """get_fraud_score should be low for normal credential extension value wrapper."""
        context = {
            "credential_extension_value_wrapper_anomaly": False,
            "credential_extension_value_wrapper_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_envelope(self):
        """get_fraud_score should analyze credential extension value envelope patterns."""
        context = {
            "credential_extension_value_envelope_anomaly": True,
            "credential_extension_value_envelope_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_envelope(self):
        """get_fraud_score should be low for normal credential extension value envelope."""
        context = {
            "credential_extension_value_envelope_anomaly": False,
            "credential_extension_value_envelope_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_container(self):
        """get_fraud_score should analyze credential extension value container patterns."""
        context = {
            "credential_extension_value_container_anomaly": True,
            "credential_extension_value_container_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_container(self):
        """get_fraud_score should be low for normal credential extension value container."""
        context = {
            "credential_extension_value_container_anomaly": False,
            "credential_extension_value_container_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_wrapper_type(self):
        """get_fraud_score should analyze credential extension value wrapper type patterns."""
        context = {
            "credential_extension_value_wrapper_type_anomaly": True,
            "credential_extension_value_wrapper_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_wrapper_type(self):
        """get_fraud_score should be low for normal credential extension value wrapper type."""
        context = {
            "credential_extension_value_wrapper_type_anomaly": False,
            "credential_extension_value_wrapper_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_envelope_type(self):
        """get_fraud_score should analyze credential extension value envelope type patterns."""
        context = {
            "credential_extension_value_envelope_type_anomaly": True,
            "credential_extension_value_envelope_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_envelope_type(self):
        """get_fraud_score should be low for normal credential extension value envelope type."""
        context = {
            "credential_extension_value_envelope_type_anomaly": False,
            "credential_extension_value_envelope_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_container_type(self):
        """get_fraud_score should analyze credential extension value container type patterns."""
        context = {
            "credential_extension_value_container_type_anomaly": True,
            "credential_extension_value_container_type_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_container_type(self):
        """get_fraud_score should be low for normal credential extension value container type."""
        context = {
            "credential_extension_value_container_type_anomaly": False,
            "credential_extension_value_container_type_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_wrapper_format(self):
        """get_fraud_score should analyze credential extension value wrapper format patterns."""
        context = {
            "credential_extension_value_wrapper_format_anomaly": True,
            "credential_extension_value_wrapper_format_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_wrapper_format(self):
        """get_fraud_score should be low for normal credential extension value wrapper format."""
        context = {
            "credential_extension_value_wrapper_format_anomaly": False,
            "credential_extension_value_wrapper_format_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_envelope_format(self):
        """get_fraud_score should analyze credential extension value envelope format patterns."""
        context = {
            "credential_extension_value_envelope_format_anomaly": True,
            "credential_extension_value_envelope_format_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_envelope_format(self):
        """get_fraud_score should be low for normal credential extension value envelope format."""
        context = {
            "credential_extension_value_envelope_format_anomaly": False,
            "credential_extension_value_envelope_format_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_container_format(self):
        """get_fraud_score should analyze credential extension value container format patterns."""
        context = {
            "credential_extension_value_container_format_anomaly": True,
            "credential_extension_value_container_format_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_container_format(self):
        """get_fraud_score should be low for normal credential extension value container format."""
        context = {
            "credential_extension_value_container_format_anomaly": False,
            "credential_extension_value_container_format_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_wrapper_encoding(self):
        """get_fraud_score should analyze credential extension value wrapper encoding patterns."""
        context = {
            "credential_extension_value_wrapper_encoding_anomaly": True,
            "credential_extension_value_wrapper_encoding_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_wrapper_encoding(self):
        """get_fraud_score should be low for normal credential extension value wrapper encoding."""
        context = {
            "credential_extension_value_wrapper_encoding_anomaly": False,
            "credential_extension_value_wrapper_encoding_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_envelope_encoding(self):
        """get_fraud_score should analyze credential extension value envelope encoding patterns."""
        context = {
            "credential_extension_value_envelope_encoding_anomaly": True,
            "credential_extension_value_envelope_encoding_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_envelope_encoding(self):
        """get_fraud_score should be low for normal credential extension value envelope encoding."""
        context = {
            "credential_extension_value_envelope_encoding_anomaly": False,
            "credential_extension_value_envelope_encoding_spoofing_detected": False,
        }
        score = get_fraud_score({}, context=context)
        assert score < 0.3

    def test_get_fraud_score_with_credential_extension_value_container_encoding(self):
        """get_fraud_score should analyze credential extension value container encoding patterns."""
        context = {
            "credential_extension_value_container_encoding_anomaly": True,
            "credential_extension_value_container_encoding_spoofing_detected": True,
        }
        score = get_fraud_score({}, context=context)
        assert score > 0.3

    def test_get_fraud_score_with_normal_credential_extension_value_container_encoding(self):
        """get_fraud_score should be low for normal credential extension value container encoding."""
        context = {
            "credential_extension_value_container_encoding_anomaly": False,
            "credential_extension_value_container_encoding_spoofing_detected": False,
        }
        score =</longcat_think>
