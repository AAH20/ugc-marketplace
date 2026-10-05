"""Comprehensive tests for broker dashboard routes."""
import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401


class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary."""

    def test_empty_dashboard(self, client):
        """Dashboard summary with no data."""
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["brokers"]["total"] == 0
        assert data["brokers"]["active"] == 0
        assert data["commissions"]["total"] == 0
        assert data["payouts"]["total"] == 0

    def test_dashboard_with_brokers(self, client, sample_broker):
        """Dashboard counts brokers correctly."""
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["brokers"]["total"] >= 1
        assert data["brokers"]["active"] >= 1

    def test_dashboard_with_inactive_broker(self, client, sample_broker_data):
        """Dashboard counts inactive brokers."""
        sample_broker_data["is_active"] = False
        client.post("/api/v1/brokers", json=sample_broker_data)
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["brokers"]["total"] >= 1
        assert data["brokers"]["active"] == 0

    def test_dashboard_with_commissions(self, client, sample_broker, sample_commission_data):
        """Dashboard counts commissions correctly."""
        client.post("/api/v1/commissions", json=sample_commission_data)
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["commissions"]["total"] >= 1
        assert data["commissions"]["pending"] >= 1

    def test_dashboard_with_payouts(self, client, sample_broker, sample_payout_data):
        """Dashboard counts payouts correctly."""
        client.post("/api/v1/payouts", json=sample_payout_data)
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["payouts"]["total"] >= 1
        assert data["payouts"]["scheduled"] >= 1

    def test_dashboard_with_campaigns(self, client, sample_campaign_data, db_session):
        """Dashboard counts campaigns correctly."""
        from app.models.campaign import Campaign
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["campaigns"]["total"] >= 1
        assert data["campaigns"]["active"] >= 1

    def test_dashboard_with_alerts(self, client, sample_campaign_data, db_session):
        """Dashboard counts unresolved alerts."""
        from app.models.campaign import Campaign
        from app.models.alert import Alert, AlertType, AlertSeverity
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
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
        response = client.get("/api/v1/dashboard/summary")
        data = response.json()
        assert data["alerts"]["unresolved"] >= 1


class TestBrokerDashboard:
    """Tests for GET /api/v1/dashboard/broker/{broker_id}."""

    def test_broker_dashboard_not_found(self, client):
        """Returns 404 for non-existent broker."""
        response = client.get("/api/v1/dashboard/broker/9999")
        assert response.status_code == 404

    def test_broker_dashboard_empty(self, client, sample_broker):
        """Dashboard for broker with no commissions/payouts."""
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["broker"]["id"] == sample_broker["id"]
        assert data["commissions"]["total_count"] == 0
        assert data["payouts"]["total_count"] == 0
        assert data["partners"]["total_count"] == 0

    def test_broker_dashboard_with_commissions(self, client, sample_broker, sample_commission_data):
        """Dashboard shows commission data."""
        client.post("/api/v1/commissions", json=sample_commission_data)
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")
        data = response.json()
        assert data["commissions"]["total_count"] == 1
        assert data["commissions"]["total_amount"] == 500.00
        assert data["commissions"]["by_status"]["pending"] == 1

    def test_broker_dashboard_with_payouts(self, client, sample_broker, sample_payout_data):
        """Dashboard shows payout data."""
        client.post("/api/v1/payouts", json=sample_payout_data)
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")
        data = response.json()
        assert data["payouts"]["total_count"] == 1
        assert data["payouts"]["total_amount"] == 5000.00
        assert data["payouts"]["by_status"]["scheduled"] == 1

    def test_broker_dashboard_with_partners(self, client, sample_broker, db_session):
        """Dashboard shows partner data."""
        from app.models.broker_partner import BrokerPartner
        partner = BrokerPartner(
            broker_id=sample_broker["id"],
            partner_name="Test Partner",
            is_active=True,
        )
        db_session.add(partner)
        db_session.commit()
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")
        data = response.json()
        assert data["partners"]["total_count"] == 1
        assert data["partners"]["active_count"] == 1

    def test_broker_dashboard_multiple_commissions(self, client, sample_broker, sample_commission_data):
        """Dashboard aggregates multiple commissions."""
        client.post("/api/v1/commissions", json=sample_commission_data)
        sample_commission_data["deal_id"] = "DEAL-002"
        sample_commission_data["commission_amount"] = 1000.00
        client.post("/api/v1/commissions", json=sample_commission_data)
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")
        data = response.json()
        assert data["commissions"]["total_count"] == 2
        assert data["commissions"]["total_amount"] == 1500.00


class TestCampaignPerformance:
    """Tests for GET /api/v1/dashboard/campaigns/{campaign_id}/performance."""

    def test_campaign_performance_not_found(self, client):
        """Returns 404 for non-existent campaign."""
        response = client.get("/api/v1/dashboard/campaigns/9999/performance")
        assert response.status_code == 404

    def test_campaign_performance_empty(self, client, sample_campaign_data, db_session):
        """Performance for campaign with no metrics."""
        from app.models.campaign import Campaign
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        campaign_id = campaign.id
        response = client.get(f"/api/v1/dashboard/campaigns/{campaign_id}/performance")
        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_impressions"] == 0
        assert data["metrics"]["ctr"] == 0
        assert data["metrics"]["roas"] == 0

    def test_campaign_performance_with_metrics(self, client, sample_campaign_data, db_session):
        """Performance with actual metrics."""
        from app.models.campaign import Campaign
        from app.models.campaign_metric import CampaignMetric
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        metric = CampaignMetric(
            campaign_id=campaign.id,
            impressions=10000,
            clicks=100,
            conversions=10,
            spend=500.00,
            revenue=1000.00,
        )
        db_session.add(metric)
        db_session.commit()
        campaign_id = campaign.id
        response = client.get(f"/api/v1/dashboard/campaigns/{campaign_id}/performance")
        data = response.json()
        assert data["metrics"]["total_impressions"] == 10000
        assert data["metrics"]["total_clicks"] == 100
        assert data["metrics"]["ctr"] == 0.01
        assert data["metrics"]["roas"] == 2.0


class TestAlertsEndpoint:
    """Tests for GET /api/v1/dashboard/alerts."""

    def test_alerts_empty(self, client):
        """Returns empty list when no alerts."""
        response = client.get("/api/v1/dashboard/alerts")
        assert response.status_code == 200
        assert response.json() == []

    def test_alerts_with_data(self, client, sample_campaign_data, db_session):
        """Returns alerts when they exist."""
        from app.models.campaign import Campaign
        from app.models.alert import Alert, AlertType, AlertSeverity
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
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
        response = client.get("/api/v1/dashboard/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["alert_type"] == "spend_spike"
        assert data[0]["severity"] == "high"

    def test_alerts_filter_by_severity(self, client, sample_campaign_data, db_session):
        """Filter alerts by severity."""
        from app.models.campaign import Campaign
        from app.models.alert import Alert, AlertType, AlertSeverity
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        for severity in AlertSeverity:
            alert = Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=severity,
                message=f"Alert {severity.value}",
                metric_value=100.0,
                threshold=50.0,
            )
            db_session.add(alert)
        db_session.commit()
        response = client.get("/api/v1/dashboard/alerts?severity=high")
        data = response.json()
        assert len(data) >= 1
        for alert in data:
            assert alert["severity"] == "high"

    def test_alerts_filter_by_resolved(self, client, sample_campaign_data, db_session):
        """Filter alerts by resolved status."""
        from app.models.campaign import Campaign
        from app.models.alert import Alert, AlertType, AlertSeverity
        campaign = Campaign(**sample_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        alert = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="Test alert",
            metric_value=100.0,
            threshold=50.0,
            is_resolved=True,
        )
        db_session.add(alert)
        db_session.commit()
        response = client.get("/api/v1/dashboard/alerts?resolved=false")
        data = response.json()
        for alert in data:
            assert alert["is_resolved"] is False
