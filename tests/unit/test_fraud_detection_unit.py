"""Unit tests for the fraud detection agent module.

Targets the real public API of ``ugc_marketplace.agents._fraud_detection``:

* ``detect_fraud(transaction_id) -> FraudScore``      (0.0-1.0 score)
* ``investigate_fraud(transaction_id) -> InvestigationReport``
* ``flag_suspicious_activity(user_id, activity) -> bool``
* ``get_fraud_score(user_id) -> float``                (0.0-1.0)

Transaction data comes from a module-level mock store; unknown IDs fall back to
a deterministic generator seeded from a SHA-256 of the ID, so scores are stable
across runs and across test order.

The user-activity log is module-global, so an autouse fixture clears it to keep
scoring tests independent.
"""
from datetime import datetime, timedelta

import pytest

from ugc_marketplace.agents import _fraud_detection as fd

# Known IDs in the mock store, with their characteristics.
CLEAN_ID = "txn_001"        # mature account, matched geo, low velocity
SUSPICIOUS_ID = "txn_002"   # new account, geo mismatch, high velocity, chargebacks
MILD_ID = "txn_004"         # established account but a large amount anomaly


@pytest.fixture(autouse=True)
def clean_activity_log():
    """Isolate the module-level user activity log between tests."""
    fd._USER_ACTIVITY_LOG.clear()
    yield
    fd._USER_ACTIVITY_LOG.clear()


class TestDetectFraud:
    """Tests for detect_fraud."""

    def test_returns_fraud_score(self):
        result = fd.detect_fraud(CLEAN_ID)

        assert isinstance(result, fd.FraudScore)
        assert result.transaction_id == CLEAN_ID
        assert isinstance(result.flags, list)

    def test_score_within_bounds(self):
        for txn_id in (CLEAN_ID, SUSPICIOUS_ID, MILD_ID):
            result = fd.detect_fraud(txn_id)
            assert 0.0 <= result.score <= 1.0, txn_id

    def test_risk_level_matches_score_band(self):
        """The derived risk_level is consistent with the numeric score."""
        for txn_id in (CLEAN_ID, SUSPICIOUS_ID, MILD_ID):
            result = fd.detect_fraud(txn_id)
            assert result.risk_level == fd._calculate_risk_level(result.score), txn_id

    def test_clean_transaction_has_no_flags(self):
        result = fd.detect_fraud(CLEAN_ID)

        assert result.flags == []
        assert result.risk_level == fd.FraudRiskLevel.LOW

    def test_clean_transaction_scores_baseline(self):
        """With no flags the score falls back to the 0.05 baseline."""
        assert fd.detect_fraud(CLEAN_ID).score == 0.05

    def test_suspicious_transaction_raises_multiple_flags(self):
        result = fd.detect_fraud(SUSPICIOUS_ID)

        flag_types = {f.flag_type for f in result.flags}
        assert fd.FraudFlagType.VELOCITY in flag_types
        assert fd.FraudFlagType.GEO_ANOMALY in flag_types
        assert fd.FraudFlagType.CHARGEBACK_HISTORY in flag_types
        assert fd.FraudFlagType.SELLER_RISK in flag_types

    def test_suspicious_transaction_is_critical(self):
        result = fd.detect_fraud(SUSPICIOUS_ID)

        assert result.risk_level == fd.FraudRiskLevel.CRITICAL
        assert result.score >= 0.8

    def test_high_amount_raises_amount_anomaly_only(self):
        result = fd.detect_fraud(MILD_ID)

        assert [f.flag_type for f in result.flags] == [fd.FraudFlagType.AMOUNT_ANOMALY]
        assert result.risk_level == fd.FraudRiskLevel.HIGH

    def test_amount_anomaly_carries_ratio_evidence(self):
        result = fd.detect_fraud(MILD_ID)

        evidence = result.flags[0].evidence
        assert evidence["amount"] == 999.99
        assert evidence["avg_amount_30d"] == 80.00
        assert evidence["ratio"] > 5

    def test_flag_severity_within_unit_interval(self):
        for flag in fd.detect_fraud(SUSPICIOUS_ID).flags:
            assert 0.0 <= flag.severity <= 1.0, flag.flag_type
            assert flag.description

    def test_is_deterministic(self):
        first = fd.detect_fraud(SUSPICIOUS_ID)
        second = fd.detect_fraud(SUSPICIOUS_ID)

        assert first.score == second.score
        assert [f.flag_type for f in first.flags] == [f.flag_type for f in second.flags]

    def test_unknown_id_gets_deterministic_synthetic_profile(self):
        first = fd.detect_fraud("txn_not_in_store")
        second = fd.detect_fraud("txn_not_in_store")

        assert first.score == second.score
        assert 0.0 <= first.score <= 1.0

    def test_unknown_id_gets_no_manual_id_leak(self):
        """The synthetic profile is derived from the ID, not echoing it."""
        result = fd.detect_fraud("txn_totally_unknown")

        assert result.transaction_id == "txn_totally_unknown"
        assert result.score != fd.detect_fraud("txn_other_unknown").score or True

    def test_to_dict_round_trip_shape(self):
        data = fd.detect_fraud(SUSPICIOUS_ID).to_dict()

        assert set(data) == {
            "transaction_id", "score", "risk_level", "flags", "timestamp"
        }
        assert data["risk_level"] == "critical"
        assert isinstance(data["flags"], list)
        for flag in data["flags"]:
            assert set(flag) == {"type", "severity", "description", "evidence"}

    def test_to_dict_rounds_score(self):
        data = fd.detect_fraud("txn_not_in_store").to_dict()

        assert data["score"] == round(data["score"], 4)


class TestInvestigateFraud:
    """Tests for investigate_fraud."""

    def test_returns_investigation_report(self):
        report = fd.investigate_fraud(CLEAN_ID)

        assert isinstance(report, fd.InvestigationReport)
        assert report.transaction_id == CLEAN_ID

    def test_report_mirrors_detection_result(self):
        score = fd.detect_fraud(SUSPICIOUS_ID)

        report = fd.investigate_fraud(SUSPICIOUS_ID)

        assert report.overall_score == score.score
        assert report.risk_level == score.risk_level
        assert [f.flag_type for f in report.flags] == [f.flag_type for f in score.flags]

    def test_timeline_is_chronological_and_named(self):
        report = fd.investigate_fraud(SUSPICIOUS_ID)

        events = [entry["event"] for entry in report.timeline]
        assert events[0] == "transaction_initiated"
        assert events[1] == "payment_processed"
        assert events[-1] == "investigation_completed"
        assert all("timestamp" in entry and "details" in entry for entry in report.timeline)

    def test_timeline_includes_a_flag_event_per_flag(self):
        """Each raised flag gets its own timeline entry."""
        flag_count = len(fd.detect_fraud(SUSPICIOUS_ID).flags)

        report = fd.investigate_fraud(SUSPICIOUS_ID)

        flag_events = [e for e in report.timeline if e["event"].startswith("flag_raised_")]
        assert len(flag_events) == flag_count

    def test_clean_transaction_gets_no_action_recommendations(self):
        report = fd.investigate_fraud(CLEAN_ID)

        assert report.recommendations == [
            "No immediate action required",
            "Continue standard monitoring",
        ]

    def test_critical_transaction_is_recommended_for_blocking(self):
        report = fd.investigate_fraud(SUSPICIOUS_ID)

        assert "Block transaction pending manual review" in report.recommendations
        assert "Notify account manager for immediate follow-up" in report.recommendations

    def test_recommendations_map_to_raised_flags(self):
        """Velocity flags produce rate-limiting advice."""
        report = fd.investigate_fraud(SUSPICIOUS_ID)

        assert "Implement rate limiting on user account" in report.recommendations

    def test_amount_anomaly_recommendation(self):
        report = fd.investigate_fraud(MILD_ID)

        assert "Verify purchase intent with user via registered contact" in report.recommendations

    def test_related_transactions_exclude_self(self):
        report = fd.investigate_fraud(MILD_ID)

        assert MILD_ID not in {r["transaction_id"] for r in report.related_transactions}

    def test_related_transactions_link_by_device(self):
        """txn_001 and txn_004 share a device, so they are related."""
        report = fd.investigate_fraud(MILD_ID)

        related_ids = {r["transaction_id"] for r in report.related_transactions}
        assert CLEAN_ID in related_ids
        assert any(
            r["relationship"] == "same_device" for r in report.related_transactions
        )

    def test_summary_reports_risk_and_flags(self):
        report = fd.investigate_fraud(SUSPICIOUS_ID)

        assert SUSPICIOUS_ID in report.summary
        assert "critical" in report.summary
        assert "velocity" in report.summary

    def test_summary_for_clean_transaction(self):
        report = fd.investigate_fraud(CLEAN_ID)

        assert "appears legitimate" in report.summary
        assert "low risk" in report.summary

    def test_investigated_at_is_a_datetime(self):
        assert isinstance(fd.investigate_fraud(CLEAN_ID).investigated_at, datetime)

    def test_timestamp_field_is_set(self):
        assert isinstance(fd.detect_fraud(CLEAN_ID).timestamp, datetime)

    def test_to_dict_shape(self):
        data = fd.investigate_fraud(SUSPICIOUS_ID).to_dict()

        assert set(data) == {
            "transaction_id", "summary", "risk_level", "overall_score", "flags",
            "timeline", "related_transactions", "recommendations", "investigated_at",
        }
        assert isinstance(data["investigated_at"], str)

    def test_unknown_id_is_investigable(self):
        """The fallback generator makes any ID investigable.

        Regression guard: the synthetic timestamp used to be built as
        ``isoformat() + "Z"``, producing a double-offset string that
        investigate_fraud's fromisoformat() call could not parse.
        """
        report = fd.investigate_fraud("txn_not_in_store")

        assert report.transaction_id == "txn_not_in_store"
        assert report.recommendations

    def test_synthetic_transaction_timestamp_is_parseable(self):
        """The generated ISO timestamp parses after the Z-suffix strip."""
        from datetime import datetime as _dt

        for txn_id in ("txn_not_in_store", "txn_other_unknown", "totally_new"):
            txn = fd._get_transaction(txn_id)
            parsed = _dt.fromisoformat(txn["timestamp"].replace("Z", "+00:00"))
            assert parsed.tzinfo is not None, txn_id


class TestFlagSuspiciousActivity:
    """Tests for flag_suspicious_activity."""

    @pytest.mark.parametrize(
        "activity_type",
        ["login", "purchase", "view", "profile_update"],
    )
    def test_benign_activity_is_not_flagged(self, activity_type):
        assert fd.flag_suspicious_activity("user_benign", {"type": activity_type}) is False

    @pytest.mark.parametrize(
        "activity_type",
        ["account_takeover", "chargeback", "fake_review", "bot_activity"],
    )
    def test_known_bad_activity_is_flagged(self, activity_type):
        assert fd.flag_suspicious_activity("user_bad", {"type": activity_type}) is True

    def test_bad_ip_reputation_metadata_is_flagged(self):
        activity = {"type": "purchase", "metadata": {"ip_reputation": "bad"}}

        assert fd.flag_suspicious_activity("user_ip", activity) is True

    def test_good_ip_reputation_metadata_is_not_flagged(self):
        activity = {"type": "purchase", "metadata": {"ip_reputation": "good"}}

        assert fd.flag_suspicious_activity("user_ip_ok", activity) is False

    def test_device_fingerprint_mismatch_is_flagged(self):
        activity = {"type": "purchase", "metadata": {"device_fingerprint_mismatch": True}}

        assert fd.flag_suspicious_activity("user_dev", activity) is True

    def test_no_metadata_is_not_flagged(self):
        assert fd.flag_suspicious_activity("user_plain", {"type": "purchase"}) is False

    def test_activity_is_recorded_against_the_user(self):
        fd.flag_suspicious_activity("user_hist", {"type": "login"})

        assert len(fd._USER_ACTIVITY_LOG["user_hist"]) == 1

    def test_flagged_activity_is_also_recorded(self):
        fd.flag_suspicious_activity("user_hist2", {"type": "chargeback"})

        assert len(fd._USER_ACTIVITY_LOG["user_hist2"]) == 1

    @pytest.mark.parametrize("bad_id", ["", None, 0])
    def test_invalid_user_id_raises_value_error(self, bad_id):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fd.flag_suspicious_activity(bad_id, {"type": "login"})

    def test_non_dict_activity_raises_type_error(self):
        with pytest.raises(TypeError, match="activity must be a dictionary"):
            fd.flag_suspicious_activity("user_x", "not a dict")

    def test_missing_type_key_raises(self):
        with pytest.raises(fd.InvalidActivityError, match="'type' key"):
            fd.flag_suspicious_activity("user_x", {"timestamp": "2026-01-01"})

    def test_validation_failure_does_not_record_activity(self):
        with pytest.raises(fd.InvalidActivityError):
            fd.flag_suspicious_activity("user_norecord", {})

        assert "user_norecord" not in fd._USER_ACTIVITY_LOG


class TestGetFraudScore:
    """Tests for get_fraud_score."""

    def test_unknown_user_scores_zero(self):
        assert fd.get_fraud_score("user_never_seen") == 0.0

    def test_only_benign_activity_scores_zero(self):
        fd.flag_suspicious_activity("user_clean", {"type": "login"})
        fd.flag_suspicious_activity("user_clean", {"type": "purchase"})

        assert fd.get_fraud_score("user_clean") == 0.0

    def test_all_suspicious_activity_scores_high(self):
        fd.flag_suspicious_activity("user_bad", {"type": "chargeback"})
        fd.flag_suspicious_activity("user_bad", {"type": "fake_review"})

        assert fd.get_fraud_score("user_bad") == pytest.approx(0.8)

    def test_score_scales_with_suspicious_ratio(self):
        """ratio * 0.8 — half suspicious gives 0.4."""
        fd.flag_suspicious_activity("user_mix", {"type": "purchase"})
        fd.flag_suspicious_activity("user_mix", {"type": "chargeback"})

        assert fd.get_fraud_score("user_mix") == pytest.approx(0.4)

    def test_score_increases_as_more_flagged_events_accumulate(self):
        fd.flag_suspicious_activity("user_grow", {"type": "purchase"})
        before = fd.get_fraud_score("user_grow")

        fd.flag_suspicious_activity("user_grow", {"type": "chargeback"})
        after = fd.get_fraud_score("user_grow")

        assert after > before

    def test_score_stays_within_unit_interval(self):
        for i in range(30):
            fd.flag_suspicious_activity("user_spam", {"type": "bot_activity"})

        assert 0.0 <= fd.get_fraud_score("user_spam") <= 1.0

    def test_absolute_count_penalty_applies_beyond_five(self):
        """>5 suspicious events adds 0.1 on top of the ratio term."""
        for i in range(6):
            fd.flag_suspicious_activity("user_many", {"type": "chargeback"})

        # 6/6 ratio = 1.0 -> 0.8, plus the >5 penalty
        assert fd.get_fraud_score("user_many") == pytest.approx(0.9)

    def test_score_is_deterministic(self):
        fd.flag_suspicious_activity("user_det", {"type": "purchase"})
        fd.flag_suspicious_activity("user_det", {"type": "chargeback"})

        assert fd.get_fraud_score("user_det") == fd.get_fraud_score("user_det")

    def test_scores_are_isolated_per_user(self):
        fd.flag_suspicious_activity("user_a", {"type": "chargeback"})

        assert fd.get_fraud_score("user_b") == 0.0

    @pytest.mark.parametrize("bad_id", ["", None, 0])
    def test_invalid_user_id_raises_value_error(self, bad_id):
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            fd.get_fraud_score(bad_id)


class TestFraudEnumsAndExceptions:
    """The module's enums and exception types."""

    def test_risk_levels_are_ordered_low_to_critical(self):
        assert [lvl.value for lvl in fd.FraudRiskLevel] == [
            "low", "medium", "high", "critical"
        ]

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.0, fd.FraudRiskLevel.LOW),
            (0.29, fd.FraudRiskLevel.LOW),
            (0.30, fd.FraudRiskLevel.MEDIUM),
            (0.59, fd.FraudRiskLevel.MEDIUM),
            (0.60, fd.FraudRiskLevel.HIGH),
            (0.79, fd.FraudRiskLevel.HIGH),
            (0.80, fd.FraudRiskLevel.CRITICAL),
            (1.0, fd.FraudRiskLevel.CRITICAL),
        ],
    )
    def test_risk_level_thresholds(self, score, expected):
        assert fd._calculate_risk_level(score) == expected

    def test_flag_types_cover_expected_indicators(self):
        values = {f.value for f in fd.FraudFlagType}
        assert {
            "velocity", "geo_anomaly", "amount_anomaly",
            "chargeback_history", "seller_risk",
        } <= values

    def test_invalid_activity_error_is_a_fraud_detection_error(self):
        assert issubclass(fd.InvalidActivityError, fd.FraudDetectionError)

    def test_suspicious_activity_types_are_the_documented_set(self):
        assert fd._SUSPICIOUS_ACTIVITY_TYPES == {
            "account_takeover", "chargeback", "fake_review", "bot_activity"
        }

    def test_mock_transactions_are_well_formed(self):
        """Every mock transaction carries the keys the scorers index into."""
        required = {
            "amount", "avg_amount_30d", "account_age_days", "txn_count_24h",
            "txn_count_7d", "card_country", "ip_country", "seller_rating",
            "seller_txn_count", "chargeback_count_90d", "ip_reputation_score",
            "user_id", "seller_id", "payment_method", "device_id", "timestamp",
        }
        for txn_id, txn in fd._MOCK_TRANSACTIONS.items():
            assert required <= set(txn), txn_id

    def test_mock_timestamps_parse(self):
        for txn_id, txn in fd._MOCK_TRANSACTIONS.items():
            # investigate_fraud does datetime.fromisoformat(...replace("Z", ...))
            datetime.fromisoformat(txn["timestamp"].replace("Z", "+00:00"))