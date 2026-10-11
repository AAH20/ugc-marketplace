"""Comprehensive tests for services: alerting, metrics, recommendations."""
import pytest
from app import models  # noqa: F401
from app.services.alerting import AlertingService
from app.services.metrics import MetricsService
from app.services.recommendations import RecommendationEngine
from app.models.alert import AlertType, AlertSeverity
from app.models.recommendation import RecommendationCategory


class TestAlertingService:
    """Tests for AlertingService."""

    def test_detect_spend_spike_normal(self):
        """No alert when spend is normal."""
        service = AlertingService()
        alerts = service.detect_spend_spike(100, 100, 1)
        assert len(alerts) == 0

    def test_detect_spend_spike_triggered(self):
        """Alert when spend exceeds threshold."""
        service = AlertingService(spend_spike_threshold=2.0)
        alerts = service.detect_spend_spike(250, 100, 1)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.SPEND_SPIKE

    def test_detect_spend_spike_critical(self):
        """Critical severity for extreme spike."""
        service = AlertingService(spend_spike_threshold=2.0)
        alerts = service.detect_spend_spike(1000, 100, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.CRITICAL

    def test_detect_spend_spike_high(self):
        """High severity for moderate spike."""
        service = AlertingService(spend_spike_threshold=2.0)
        alerts = service.detect_spend_spike(300, 100, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.HIGH

    def test_detect_spend_spike_zero_avg(self):
        """No alert when average spend is zero."""
        service = AlertingService()
        alerts = service.detect_spend_spike(100, 0, 1)
        assert len(alerts) == 0

    def test_detect_ctr_drop_normal(self):
        """No alert when CTR is normal."""
        service = AlertingService()
        alerts = service.detect_ctr_drop(0.01, 0.01, 1)
        assert len(alerts) == 0

    def test_detect_ctr_drop_triggered(self):
        """Alert when CTR drops significantly."""
        service = AlertingService(ctr_drop_threshold=0.5)
        alerts = service.detect_ctr_drop(0.003, 0.01, 1)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.CTR_DROP

    def test_detect_ctr_drop_high_severity(self):
        """High severity for extreme drop."""
        service = AlertingService(ctr_drop_threshold=0.5)
        alerts = service.detect_ctr_drop(0.001, 0.01, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.HIGH

    def test_detect_ctr_drop_medium_severity(self):
        """Medium severity for moderate drop."""
        service = AlertingService(ctr_drop_threshold=0.5)
        alerts = service.detect_ctr_drop(0.004, 0.01, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.MEDIUM

    def test_detect_ctr_drop_zero_baseline(self):
        """No alert when baseline CTR is zero."""
        service = AlertingService()
        alerts = service.detect_ctr_drop(0.005, 0, 1)
        assert len(alerts) == 0

    def test_detect_low_roas_normal(self):
        """No alert when ROAS meets target."""
        service = AlertingService()
        alerts = service.detect_low_roas(2.5, 2.0, 1)
        assert len(alerts) == 0

    def test_detect_low_roas_triggered(self):
        """Alert when ROAS is below target."""
        service = AlertingService(min_roas_threshold=2.0)
        alerts = service.detect_low_roas(1.0, 2.0, 1)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.LOW_ROAS

    def test_detect_low_roas_critical(self):
        """Critical severity for extreme gap."""
        service = AlertingService(min_roas_threshold=2.0)
        alerts = service.detect_low_roas(0.3, 2.0, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.CRITICAL

    def test_detect_low_roas_high(self):
        """High severity for moderate gap."""
        service = AlertingService(min_roas_threshold=2.0)
        alerts = service.detect_low_roas(1.0, 2.0, 1)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == AlertSeverity.HIGH

    def test_detect_all_combined(self):
        """detect_all combines all detectors."""
        service = AlertingService(
            spend_spike_threshold=2.0,
            ctr_drop_threshold=0.5,
            min_roas_threshold=2.0,
        )
        alerts = service.detect_all(
            campaign_id=1,
            current_spend=300,
            avg_spend=100,
            current_ctr=0.003,
            baseline_ctr=0.01,
            current_roas=1.0,
            target_roas=2.0,
        )
        assert len(alerts) == 3
        types = {a["alert_type"] for a in alerts}
        assert AlertType.SPEND_SPIKE in types
        assert AlertType.CTR_DROP in types
        assert AlertType.LOW_ROAS in types

    def test_detect_all_no_alerts(self):
        """detect_all returns empty when all metrics normal."""
        service = AlertingService()
        alerts = service.detect_all(
            campaign_id=1,
            current_spend=100,
            avg_spend=100,
            current_ctr=0.01,
            baseline_ctr=0.01,
            current_roas=2.5,
            target_roas=2.0,
        )
        assert len(alerts) == 0


class TestMetricsService:
    """Tests for MetricsService."""

    def test_compute_ctr(self):
        """CTR is clicks / impressions."""
        service = MetricsService()
        assert service.compute_ctr(100, 10000) == 0.01

    def test_compute_ctr_zero_impressions(self):
        """CTR is 0 when no impressions."""
        service = MetricsService()
        assert service.compute_ctr(100, 0) == 0.0

    def test_compute_roas(self):
        """ROAS is revenue / spend."""
        service = MetricsService()
        assert service.compute_roas(1000, 500) == 2.0

    def test_compute_roas_zero_spend(self):
        """ROAS is 0 when no spend."""
        service = MetricsService()
        assert service.compute_roas(1000, 0) == 0.0

    def test_compute_cpc(self):
        """CPC is spend / clicks."""
        service = MetricsService()
        assert service.compute_cpc(500, 100) == 5.0

    def test_compute_cpc_zero_clicks(self):
        """CPC is 0 when no clicks."""
        service = MetricsService()
        assert service.compute_cpc(500, 0) == 0.0

    def test_compute_cpm(self):
        """CPM is (spend / impressions) * 1000."""
        service = MetricsService()
        assert service.compute_cpm(500, 10000) == 50.0

    def test_compute_cpm_zero_impressions(self):
        """CPM is 0 when no impressions."""
        service = MetricsService()
        assert service.compute_cpm(500, 0) == 0.0

    def test_compute_conversion_rate(self):
        """Conversion rate is conversions / clicks."""
        service = MetricsService()
        assert service.compute_conversion_rate(10, 100) == 0.1

    def test_compute_conversion_rate_zero_clicks(self):
        """Conversion rate is 0 when no clicks."""
        service = MetricsService()
        assert service.compute_conversion_rate(10, 0) == 0.0

    def test_aggregate_empty(self):
        """Aggregate empty list returns zeros."""
        service = MetricsService()
        result = service.aggregate([])
        assert result["total_impressions"] == 0
        assert result["total_clicks"] == 0
        assert result["ctr"] == 0

    def test_aggregate_single_metric(self):
        """Aggregate single metric."""
        service = MetricsService()
        result = service.aggregate([
            {"impressions": 10000, "clicks": 100, "conversions": 10, "spend": 500, "revenue": 1000}
        ])
        assert result["total_impressions"] == 10000
        assert result["total_clicks"] == 100
        assert result["ctr"] == 0.01
        assert result["roas"] == 2.0

    def test_aggregate_multiple_metrics(self):
        """Aggregate multiple metrics."""
        service = MetricsService()
        result = service.aggregate([
            {"impressions": 10000, "clicks": 100, "conversions": 10, "spend": 500, "revenue": 1000},
            {"impressions": 20000, "clicks": 200, "conversions": 20, "spend": 1000, "revenue": 2000},
        ])
        assert result["total_impressions"] == 30000
        assert result["total_clicks"] == 300
        assert result["total_spend"] == 1500
        assert result["total_revenue"] == 3000
        assert result["ctr"] == 0.01
        assert result["roas"] == 2.0


class TestRecommendationEngine:
    """Tests for RecommendationEngine."""

    def test_generate_no_recommendations(self):
        """No recommendations when all metrics meet targets."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=2.5,
            target_roas=2.0,
            current_ctr=0.02,
            target_ctr=0.01,
            spend_trend="stable",
        )
        assert len(recs) == 0

    def test_generate_budget_reallocation(self):
        """Budget reallocation when ROAS below target."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=1.0,
            target_roas=2.0,
            current_ctr=0.02,
            target_ctr=0.01,
            spend_trend="stable",
        )
        assert len(recs) >= 1
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.BUDGET_REALLOCATION in categories

    def test_generate_ctr_optimization(self):
        """CTR optimization when CTR below target."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=2.5,
            target_roas=2.0,
            current_ctr=0.005,
            target_ctr=0.01,
            spend_trend="stable",
        )
        assert len(recs) >= 1
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.CTR_OPTIMIZATION in categories

    def test_generate_spend_adjustment(self):
        """Spend adjustment when spend trend is spike."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=2.5,
            target_roas=2.0,
            current_ctr=0.02,
            target_ctr=0.01,
            spend_trend="spike",
        )
        assert len(recs) >= 1
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.SPEND_ADJUSTMENT in categories

    def test_generate_sorted_by_priority(self):
        """Recommendations are sorted by priority."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=1.0,
            target_roas=2.0,
            current_ctr=0.005,
            target_ctr=0.01,
            spend_trend="spike",
        )
        priorities = [r["priority"] for r in recs]
        assert priorities == sorted(priorities)

    def test_generate_multiple_recommendations(self):
        """Multiple recommendations when multiple issues."""
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=1.0,
            target_roas=2.0,
            current_ctr=0.005,
            target_ctr=0.01,
            spend_trend="spike",
        )
        assert len(recs) >= 3
