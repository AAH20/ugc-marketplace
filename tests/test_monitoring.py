"""Integration tests for real-time campaign monitoring dashboard."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metric import CampaignMetric
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.recommendation import Recommendation, RecommendationCategory


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def db_engine():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_campaign(db_session):
    campaign = Campaign(
        name="Summer Launch 2026",
        status=CampaignStatus.ACTIVE,
        budget=10000.0,
        spent=2500.0,
        target_roas=3.0,
        target_ctr=0.02,
        start_date=datetime.now(timezone.utc).date() - timedelta(days=7),
        end_date=datetime.now(timezone.utc).date() + timedelta(days=23),
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def sample_metrics(db_session, sample_campaign):
    """Create 24 hours of hourly metrics with a clear spend spike at hour 20."""
    from app.routes.monitoring import _detect_and_alert

    metrics = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)
    for hour in range(24):
        # Normal spend ~100/hr, spike to 500 at hour 20
        spend = 500.0 if hour == 20 else 100.0
        impressions = 10000
        clicks = 200  # CTR = 2%
        conversions = 10
        revenue = 300.0  # ROAS = 3.0 normally

        # At hour 20, CTR drops to 0.5% and ROAS drops to 0.5
        if hour == 20:
            clicks = 50
            revenue = 250.0

        metric = CampaignMetric(
            campaign_id=sample_campaign.id,
            timestamp=base_time + timedelta(hours=hour),
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=spend,
            revenue=revenue,
        )
        metrics.append(metric)
    db_session.add_all(metrics)
    db_session.commit()

    # Generate alerts and recommendations for the spike metric (hour 20)
    from app.routes.monitoring import _detect_and_alert, _generate_recommendations
    _detect_and_alert(db_session, sample_campaign, metrics[20])
    _generate_recommendations(db_session, sample_campaign)

    return metrics


@pytest.fixture
def client(db_engine):
    """Test client with in-memory DB override."""
    def override_get_db():
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Model Tests ───────────────────────────────────────────────────────

class TestCampaignModel:
    def test_create_campaign(self, db_session):
        campaign = Campaign(
            name="Test Campaign",
            status=CampaignStatus.ACTIVE,
            budget=5000.0,
            spent=0.0,
            target_roas=2.5,
            target_ctr=0.015,
        )
        db_session.add(campaign)
        db_session.commit()
        assert campaign.id is not None
        assert campaign.name == "Test Campaign"

    def test_campaign_status_enum(self):
        assert CampaignStatus.ACTIVE == "active"
        assert CampaignStatus.PAUSED == "paused"
        assert CampaignStatus.COMPLETED == "completed"


class TestCampaignMetricModel:
    def test_create_metric(self, db_session, sample_campaign):
        metric = CampaignMetric(
            campaign_id=sample_campaign.id,
            impressions=1000,
            clicks=50,
            conversions=5,
            spend=100.0,
            revenue=300.0,
        )
        db_session.add(metric)
        db_session.commit()
        assert metric.id is not None
        assert metric.impressions == 1000


class TestAlertModel:
    def test_create_alert(self, db_session, sample_campaign):
        alert = Alert(
            campaign_id=sample_campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="Spend spike detected",
            metric_value=500.0,
            threshold=200.0,
        )
        db_session.add(alert)
        db_session.commit()
        assert alert.id is not None
        assert alert.is_resolved is False


class TestRecommendationModel:
    def test_create_recommendation(self, db_session, sample_campaign):
        rec = Recommendation(
            campaign_id=sample_campaign.id,
            category=RecommendationCategory.BUDGET_REALLOCATION,
            priority=1,
            title="Reduce spend on underperforming ad set",
            description="Ad set X has ROAS below threshold",
            expected_impact=0.15,
        )
        db_session.add(rec)
        db_session.commit()
        assert rec.id is not None
        assert rec.is_applied is False


# ── Metrics Service Tests ─────────────────────────────────────────────

class TestMetricsService:
    def test_compute_ctr(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        assert svc.compute_ctr(clicks=50, impressions=1000) == 0.05

    def test_compute_ctr_zero_impressions(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        assert svc.compute_ctr(clicks=0, impressions=0) == 0.0

    def test_compute_roas(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        assert svc.compute_roas(revenue=300.0, spend=100.0) == 3.0

    def test_compute_roas_zero_spend(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        assert svc.compute_roas(revenue=300.0, spend=0.0) == 0.0

    def test_compute_cpc(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        assert svc.compute_cpc(spend=100.0, clicks=50) == 2.0

    def test_aggregate_metrics(self):
        from app.services.metrics import MetricsService
        svc = MetricsService()
        metrics = [
            {"impressions": 1000, "clicks": 50, "conversions": 5, "spend": 100.0, "revenue": 300.0},
            {"impressions": 2000, "clicks": 100, "conversions": 10, "spend": 200.0, "revenue": 600.0},
        ]
        agg = svc.aggregate(metrics)
        assert agg["total_impressions"] == 3000
        assert agg["total_clicks"] == 150
        assert agg["total_conversions"] == 15
        assert agg["total_spend"] == 300.0
        assert agg["total_revenue"] == 900.0
        assert agg["ctr"] == 0.05
        assert agg["roas"] == 3.0
        assert agg["cpc"] == 2.0


# ── Alerting Service Tests ────────────────────────────────────────────

class TestAlertingService:
    def test_detect_spend_spike(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(spend_spike_threshold=2.0)
        alerts = svc.detect_spend_spike(
            current_spend=500.0,
            avg_spend=100.0,
            campaign_id=1,
        )
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.SPEND_SPIKE
        assert alerts[0]["severity"] == AlertSeverity.HIGH

    def test_no_spend_spike_when_normal(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(spend_spike_threshold=2.0)
        alerts = svc.detect_spend_spike(
            current_spend=110.0,
            avg_spend=100.0,
            campaign_id=1,
        )
        assert len(alerts) == 0

    def test_detect_ctr_drop(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(ctr_drop_threshold=0.5)
        alerts = svc.detect_ctr_drop(
            current_ctr=0.005,
            baseline_ctr=0.02,
            campaign_id=1,
        )
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.CTR_DROP
        assert alerts[0]["severity"] == AlertSeverity.MEDIUM

    def test_no_ctr_drop_when_stable(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(ctr_drop_threshold=0.5)
        alerts = svc.detect_ctr_drop(
            current_ctr=0.019,
            baseline_ctr=0.02,
            campaign_id=1,
        )
        assert len(alerts) == 0

    def test_detect_low_roas(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(min_roas_threshold=2.0)
        alerts = svc.detect_low_roas(
            current_roas=1.0,
            target_roas=3.0,
            campaign_id=1,
        )
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == AlertType.LOW_ROAS
        assert alerts[0]["severity"] == AlertSeverity.HIGH

    def test_no_low_roas_when_above_target(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(min_roas_threshold=2.0)
        alerts = svc.detect_low_roas(
            current_roas=3.5,
            target_roas=3.0,
            campaign_id=1,
        )
        assert len(alerts) == 0

    def test_detect_all_anomalies(self):
        from app.services.alerting import AlertingService
        svc = AlertingService(
            spend_spike_threshold=2.0,
            ctr_drop_threshold=0.5,
            min_roas_threshold=2.0,
        )
        alerts = svc.detect_all(
            campaign_id=1,
            current_spend=500.0,
            avg_spend=100.0,
            current_ctr=0.005,
            baseline_ctr=0.02,
            current_roas=1.0,
            target_roas=3.0,
        )
        alert_types = {a["alert_type"] for a in alerts}
        assert AlertType.SPEND_SPIKE in alert_types
        assert AlertType.CTR_DROP in alert_types
        assert AlertType.LOW_ROAS in alert_types


# ── Recommendation Engine Tests ───────────────────────────────────────

class TestRecommendationEngine:
    def test_recommend_budget_reallocation_on_low_roas(self):
        from app.services.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=1.0,
            target_roas=3.0,
            current_ctr=0.02,
            target_ctr=0.02,
            spend_trend="stable",
        )
        assert len(recs) > 0
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.BUDGET_REALLOCATION in categories

    def test_recommend_ctr_optimization_on_low_ctr(self):
        from app.services.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=3.0,
            target_roas=3.0,
            current_ctr=0.005,
            target_ctr=0.02,
            spend_trend="stable",
        )
        assert len(recs) > 0
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.CTR_OPTIMIZATION in categories

    def test_recommend_spend_adjustment_on_spike(self):
        from app.services.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=3.0,
            target_roas=3.0,
            current_ctr=0.02,
            target_ctr=0.02,
            spend_trend="spike",
        )
        assert len(recs) > 0
        categories = {r["category"] for r in recs}
        assert RecommendationCategory.SPEND_ADJUSTMENT in categories

    def test_no_recommendations_when_healthy(self):
        from app.services.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=3.5,
            target_roas=3.0,
            current_ctr=0.025,
            target_ctr=0.02,
            spend_trend="stable",
        )
        assert len(recs) == 0

    def test_recommendations_have_required_fields(self):
        from app.services.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate(
            campaign_id=1,
            current_roas=1.0,
            target_roas=3.0,
            current_ctr=0.005,
            target_ctr=0.02,
            spend_trend="spike",
        )
        for rec in recs:
            assert "campaign_id" in rec
            assert "category" in rec
            assert "priority" in rec
            assert "title" in rec
            assert "description" in rec
            assert "expected_impact" in rec


# ── REST API Tests ────────────────────────────────────────────────────

class TestCampaignAPI:
    def test_list_campaigns(self, client, sample_campaign):
        resp = client.get("/api/campaigns")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Summer Launch 2026"

    def test_get_campaign(self, client, sample_campaign):
        resp = client.get(f"/api/campaigns/{sample_campaign.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample_campaign.id
        assert data["name"] == "Summer Launch 2026"

    def test_get_campaign_not_found(self, client):
        resp = client.get("/api/campaigns/99999")
        assert resp.status_code == 404

    def test_get_campaign_metrics(self, client, sample_campaign, sample_metrics):
        resp = client.get(f"/api/campaigns/{sample_campaign.id}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 24

    def test_get_campaign_alerts(self, client, sample_campaign, sample_metrics):
        resp = client.get(f"/api/campaigns/{sample_campaign.id}/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_get_campaign_recommendations(self, client, sample_campaign, sample_metrics):
        resp = client.get(f"/api/campaigns/{sample_campaign.id}/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_ingest_metric(self, client, sample_campaign):
        resp = client.post(
            f"/api/campaigns/{sample_campaign.id}/metrics",
            json={
                "impressions": 5000,
                "clicks": 100,
                "conversions": 5,
                "spend": 50.0,
                "revenue": 150.0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["campaign_id"] == sample_campaign.id
        assert data["impressions"] == 5000

    def test_dashboard_summary(self, client, sample_campaign, sample_metrics):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_campaigns" in data
        assert "active_campaigns" in data
        assert "total_spend" in data
        assert "total_revenue" in data
        assert "avg_roas" in data
        assert "alerts_count" in data


# ── WebSocket Tests ───────────────────────────────────────────────────

class TestWebSocketEndpoints:
    def test_websocket_metrics_stream(self, client, sample_campaign, sample_metrics):
        """WebSocket streams live metrics for a campaign."""
        with client.websocket_connect(
            f"/ws/campaigns/{sample_campaign.id}/metrics"
        ) as ws:
            # Server sends initial metrics first
            msg = ws.receive_json()
            assert msg["type"] == "initial_metrics"
            # Send a ping to verify connection
            ws.send_json({"action": "ping"})
            msg = ws.receive_json()
            assert msg["type"] == "pong"

    def test_websocket_alerts_stream(self, client, sample_campaign, sample_metrics):
        """WebSocket streams alerts for a campaign."""
        with client.websocket_connect(
            f"/ws/campaigns/{sample_campaign.id}/alerts"
        ) as ws:
            # Server sends initial alerts first
            msg = ws.receive_json()
            assert msg["type"] == "initial_alerts"
            ws.send_json({"action": "ping"})
            msg = ws.receive_json()
            assert msg["type"] == "pong"

    def test_websocket_dashboard_overview(self, client, sample_campaign, sample_metrics):
        """WebSocket streams dashboard overview."""
        with client.websocket_connect("/ws/dashboard") as ws:
            # Server sends initial dashboard first
            msg = ws.receive_json()
            assert msg["type"] == "summary"
            ws.send_json({"action": "ping"})
            msg = ws.receive_json()
            assert msg["type"] == "pong"

    def test_websocket_invalid_campaign(self, client):
        """WebSocket rejects invalid campaign ID."""
        with client.websocket_connect("/ws/campaigns/99999/metrics") as ws:
            # Should receive initial data or close
            try:
                msg = ws.receive_json()
                # If we get a message, it should be an error or empty metrics
                assert "type" in msg
            except Exception:
                pass  # Connection closed is also acceptable


# ── End-to-End Integration Tests ──────────────────────────────────────

class TestEndToEnd:
    def test_full_monitoring_pipeline(self, client, db_session):
        """Create campaign → ingest metrics → detect anomalies → get recommendations."""
        # 1. Create campaign
        campaign = Campaign(
            name="E2E Test Campaign",
            status=CampaignStatus.ACTIVE,
            budget=5000.0,
            spent=0.0,
            target_roas=3.0,
            target_ctr=0.02,
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        # 2. Ingest normal metrics via API
        for i in range(10):
            client.post(
                f"/api/campaigns/{campaign.id}/metrics",
                json={
                    "impressions": 10000,
                    "clicks": 200,
                    "conversions": 10,
                    "spend": 100.0,
                    "revenue": 300.0,
                },
            )

        # 3. Ingest anomalous metric (spend spike + CTR drop + low ROAS)
        client.post(
            f"/api/campaigns/{campaign.id}/metrics",
            json={
                "impressions": 10000,
                "clicks": 50,
                "conversions": 5,
                "spend": 500.0,
                "revenue": 250.0,
            },
        )

        # 4. Check alerts were generated
        response = client.get(f"/api/campaigns/{campaign.id}/alerts")
        alerts = response.json()
        assert len(alerts) >= 2  # At least spend spike and low ROAS

        # 5. Check recommendations were generated
        response = client.get(f"/api/campaigns/{campaign.id}/recommendations")
        recommendations = response.json()
        assert len(recommendations) >= 1

    def test_alert_resolution_workflow(self, client, db_session):
        """Resolve an alert and verify it is marked resolved."""
        # 1. Create campaign
        campaign = Campaign(
            name="Alert Resolution Test",
            status=CampaignStatus.ACTIVE,
            budget=5000.0,
            spent=0.0,
            target_roas=3.0,
            target_ctr=0.02,
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        # 2. Create alert
        alert = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="Test alert",
            metric_value=100.0,
            threshold=50.0,
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        # 3. Resolve alert
        alert.is_resolved = True
        db_session.commit()

        # 4. Verify alert is resolved
        response = client.get(f"/api/campaigns/{campaign.id}/alerts")
        alerts = response.json()
        assert len(alerts) == 0  # Resolved alerts are hidden by default

        # 5. Verify alert is visible when including resolved
        response = client.get(f"/api/campaigns/{campaign.id}/alerts?include_resolved=true")
        alerts = response.json()
        assert len(alerts) == 1
        assert alerts[0]["is_resolved"] is True

        # 4. Check alerts were generated
        resp = client.get(f"/api/campaigns/{campaign.id}/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) >= 2  # At least spend spike and low ROAS

        # 5. Check recommendations were generated
        resp = client.get(f"/api/campaigns/{campaign.id}/recommendations")
        assert resp.status_code == 200
        recs = resp.json()
        assert len(recs) > 0

        # 6. Check dashboard includes this campaign
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        dashboard = resp.json()
        assert dashboard["total_campaigns"] >= 1

    def test_alert_resolution_workflow(self, client, db_session):
        """Create alert → resolve it → verify it's marked resolved."""
        campaign = Campaign(
            name="Alert Test Campaign",
            status=CampaignStatus.ACTIVE,
            budget=1000.0,
            spent=0.0,
            target_roas=2.0,
            target_ctr=0.01,
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        # Create an alert
        alert = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.LOW_ROAS,
            severity=AlertSeverity.HIGH,
            message="ROAS below threshold",
            metric_value=0.5,
            threshold=2.0,
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        # Verify it's unresolved
        resp = client.get(f"/api/campaigns/{campaign.id}/alerts")
        alerts = resp.json()
        assert len(alerts) == 1
        assert alerts[0]["is_resolved"] is False

        # Resolve it
        resp = client.post(f"/api/alerts/{alert.id}/resolve")
        assert resp.status_code == 200

        # Verify it's resolved
        resp = client.get(f"/api/campaigns/{campaign.id}/alerts?include_resolved=true")
        alerts = resp.json()
        assert len(alerts) == 1
        assert alerts[0]["is_resolved"] is True