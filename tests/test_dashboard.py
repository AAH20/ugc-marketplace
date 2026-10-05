"""Comprehensive tests for broker dashboard routes.

Every test that seeds rows directly takes the ``db_session`` fixture, which is
the same session the ``client`` fixture injects via the get_db dependency
override — so direct writes are visible to the routes under test.
"""
from datetime import date

import pytest

from app import models  # noqa: F401
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.broker_partner import BrokerPartner
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metric import CampaignMetric


@pytest.fixture
def campaign(db_session):
    """Persist an active campaign and return it (with its generated id)."""
    obj = Campaign(
        name="Test Campaign",
        description="A test campaign",
        status=CampaignStatus.ACTIVE,
        budget=10000.00,
        spent=5000.00,
        target_roas=2.0,
        target_ctr=0.01,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def alert(db_session, campaign):
    """Persist a high-severity unresolved alert against ``campaign``."""
    obj = Alert(
        campaign_id=campaign.id,
        alert_type=AlertType.SPEND_SPIKE,
        severity=AlertSeverity.HIGH,
        message="Test alert",
        metric_value=100.0,
        threshold=50.0,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def campaign_metric(db_session, campaign):
    """Persist a single metric row with known impressions/clicks/spend."""
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
    return metric


class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary."""

    def test_empty_dashboard(self, client):
        """Summary reports zeroed counters when no data exists."""
        response = client.get("/api/v1/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["brokers"] == {"total": 0, "active": 0}
        assert data["commissions"] == {"total": 0, "pending": 0}
        assert data["payouts"] == {"total": 0, "scheduled": 0}
        assert data["campaigns"] == {"total": 0, "active": 0}
        assert data["alerts"] == {"unresolved": 0}

    def test_dashboard_with_brokers(self, client, sample_broker):
        """Active brokers are counted in both total and active."""
        response = client.get("/api/v1/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["brokers"]["total"] == 1
        assert data["brokers"]["active"] == 1

    def test_dashboard_with_inactive_broker(self, client, sample_broker_data):
        """An inactive broker counts toward total but not toward active."""
        sample_broker_data["is_active"] = False
        client.post("/api/v1/brokers", json=sample_broker_data)

        data = client.get("/api/v1/dashboard/summary").json()

        assert data["brokers"]["total"] == 1
        assert data["brokers"]["active"] == 0

    def test_dashboard_with_commissions(self, client, sample_broker, sample_commission_data):
        """Commission totals and pending count are aggregated."""
        client.post("/api/v1/commissions", json=sample_commission_data)

        data = client.get("/api/v1/dashboard/summary").json()

        assert data["commissions"]["total"] == 1
        assert data["commissions"]["pending"] == 1

    def test_dashboard_with_payouts(self, client, sample_broker, sample_payout_data):
        """Payout totals and scheduled count are aggregated."""
        client.post("/api/v1/payouts", json=sample_payout_data)

        data = client.get("/api/v1/dashboard/summary").json()

        assert data["payouts"]["total"] == 1
        assert data["payouts"]["scheduled"] == 1

    def test_dashboard_with_campaigns(self, client, campaign):
        """Campaign totals and active count are aggregated."""
        data = client.get("/api/v1/dashboard/summary").json()

        assert data["campaigns"]["total"] == 1
        assert data["campaigns"]["active"] == 1

    def test_dashboard_counts_unresolved_alerts_only(self, client, db_session, campaign):
        """Resolved alerts are excluded from the unresolved counter."""
        unresolved = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="unresolved",
            metric_value=100.0,
            threshold=50.0,
        )
        resolved = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.LOW,
            message="resolved",
            metric_value=10.0,
            threshold=50.0,
            is_resolved=True,
        )
        db_session.add_all([unresolved, resolved])
        db_session.commit()

        data = client.get("/api/v1/dashboard/summary").json()

        assert data["alerts"]["unresolved"] == 1


class TestBrokerDashboard:
    """Tests for GET /api/v1/dashboard/broker/{broker_id}."""

    def test_broker_dashboard_not_found(self, client):
        """Returns 404 for a non-existent broker."""
        response = client.get("/api/v1/dashboard/broker/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Broker not found"

    def test_broker_dashboard_empty(self, client, sample_broker):
        """Broker with no commissions, payouts or partners reports zeros."""
        response = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["broker"]["id"] == sample_broker["id"]
        assert data["commissions"]["total_count"] == 0
        assert data["commissions"]["total_amount"] == 0.0
        assert data["payouts"]["total_count"] == 0
        assert data["partners"]["total_count"] == 0
        assert data["partners"]["active_count"] == 0

    def test_broker_dashboard_with_commissions(self, client, sample_broker, sample_commission_data):
        """Commission amount is summed and bucketed by status."""
        client.post("/api/v1/commissions", json=sample_commission_data)

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["commissions"]["total_count"] == 1
        assert data["commissions"]["total_amount"] == 500.00
        assert data["commissions"]["by_status"]["pending"] == 1

    def test_broker_dashboard_with_payouts(self, client, sample_broker, sample_payout_data):
        """Payout amount is summed and bucketed by status."""
        client.post("/api/v1/payouts", json=sample_payout_data)

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["payouts"]["total_count"] == 1
        assert data["payouts"]["total_amount"] == 5000.00
        assert data["payouts"]["by_status"]["scheduled"] == 1

    def test_broker_dashboard_with_partners(self, client, db_session, sample_broker):
        """Partner rows are counted in total and active.

        There is no partner-creation endpoint, so the row is seeded directly.
        """
        db_session.add(BrokerPartner(
            broker_id=sample_broker["id"],
            partner_name="Test Partner",
        ))
        db_session.commit()

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["partners"]["total_count"] == 1
        assert data["partners"]["active_count"] == 1

    def test_broker_dashboard_inactive_partner_not_active(self, client, db_session, sample_broker):
        """An inactive partner counts toward total but not toward active."""
        db_session.add(BrokerPartner(
            broker_id=sample_broker["id"],
            partner_name="Dormant Partner",
            is_active=False,
        ))
        db_session.commit()

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["partners"]["total_count"] == 1
        assert data["partners"]["active_count"] == 0

    def test_broker_dashboard_aggregates_multiple_commissions(
        self, client, sample_broker, sample_commission_data
    ):
        """Multiple commissions are summed into one total."""
        client.post("/api/v1/commissions", json=sample_commission_data)
        sample_commission_data["deal_id"] = "DEAL-002"
        sample_commission_data["commission_amount"] = 1000.00
        client.post("/api/v1/commissions", json=sample_commission_data)

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["commissions"]["total_count"] == 2
        assert data["commissions"]["total_amount"] == 1500.00


class TestCampaignPerformance:
    """Tests for GET /api/v1/dashboard/campaigns/{campaign_id}/performance."""

    def test_campaign_performance_not_found(self, client):
        """Returns 404 for a non-existent campaign."""
        response = client.get("/api/v1/dashboard/campaigns/9999/performance")

        assert response.status_code == 404
        assert response.json()["detail"] == "Campaign not found"

    def test_campaign_performance_empty(self, client, campaign):
        """No metrics yields zeroed counters with no division errors."""
        response = client.get(f"/api/v1/dashboard/campaigns/{campaign.id}/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == campaign.id
        assert data["metrics"]["total_impressions"] == 0
        assert data["metrics"]["ctr"] == 0
        assert data["metrics"]["roas"] == 0

    def test_campaign_performance_with_metrics(self, client, campaign, campaign_metric):
        """ctr = clicks/impressions and roas = revenue/spend."""
        response = client.get(f"/api/v1/dashboard/campaigns/{campaign.id}/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_impressions"] == 10000
        assert data["metrics"]["total_clicks"] == 100
        assert data["metrics"]["total_conversions"] == 10
        assert data["metrics"]["total_spend"] == 500.00
        assert data["metrics"]["total_revenue"] == 1000.00
        assert data["metrics"]["ctr"] == 0.01
        assert data["metrics"]["roas"] == 2.0

    def test_campaign_performance_aggregates_multiple_metrics(self, client, campaign, db_session):
        """Multiple metric rows are summed before ratios are computed.

        1000+3000 impressions, 10+60 clicks -> ctr 0.0175;
        $1000 revenue over $400 spend -> roas 2.5.
        """
        db_session.add_all([
            CampaignMetric(
                campaign_id=campaign.id, impressions=1000, clicks=10,
                conversions=1, spend=100.00, revenue=200.00,
            ),
            CampaignMetric(
                campaign_id=campaign.id, impressions=3000, clicks=60,
                conversions=4, spend=300.00, revenue=800.00,
            ),
        ])
        db_session.commit()

        data = client.get(f"/api/v1/dashboard/campaigns/{campaign.id}/performance").json()

        assert data["metrics"]["total_impressions"] == 4000
        assert data["metrics"]["total_clicks"] == 70
        assert data["metrics"]["total_conversions"] == 5
        assert data["metrics"]["total_spend"] == 400.00
        assert data["metrics"]["total_revenue"] == 1000.00
        assert data["metrics"]["ctr"] == 0.0175
        assert data["metrics"]["roas"] == 2.5


class TestAlertsEndpoint:
    """Tests for GET /api/v1/dashboard/alerts."""

    def test_alerts_empty(self, client):
        """Returns an empty list when no alerts exist."""
        response = client.get("/api/v1/dashboard/alerts")

        assert response.status_code == 200
        assert response.json() == []

    def test_alerts_with_data(self, client, alert):
        """Alert rows serialize type/severity as their enum values."""
        response = client.get("/api/v1/dashboard/alerts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["alert_type"] == "spend_spike"
        assert data[0]["severity"] == "high"
        assert data[0]["is_resolved"] is False
        assert data[0]["message"] == "Test alert"

    def test_alerts_filter_by_severity(self, client, db_session, campaign):
        """Only alerts matching the requested severity are returned."""
        for severity in AlertSeverity:
            db_session.add(Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=severity,
                message=f"Alert {severity.value}",
                metric_value=100.0,
                threshold=50.0,
            ))
        db_session.commit()

        data = client.get("/api/v1/dashboard/alerts?severity=high").json()

        assert len(data) == 1
        assert all(a["severity"] == "high" for a in data)

    def test_alerts_filter_by_unresolved(self, client, db_session, campaign):
        """resolved=false returns only unresolved alerts."""
        db_session.add_all([
            Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=AlertSeverity.HIGH,
                message="unresolved",
                metric_value=100.0,
                threshold=50.0,
            ),
            Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=AlertSeverity.HIGH,
                message="resolved",
                metric_value=100.0,
                threshold=50.0,
                is_resolved=True,
            ),
        ])
        db_session.commit()

        data = client.get("/api/v1/dashboard/alerts?resolved=false").json()

        assert len(data) == 1
        assert data[0]["message"] == "unresolved"
        assert data[0]["is_resolved"] is False

    def test_alerts_filter_by_resolved(self, client, db_session, campaign):
        """resolved=true returns only resolved alerts."""
        db_session.add(Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.LOW,
            message="resolved",
            metric_value=10.0,
            threshold=50.0,
            is_resolved=True,
        ))
        db_session.commit()

        data = client.get("/api/v1/dashboard/alerts?resolved=true").json()

        assert len(data) == 1
        assert data[0]["is_resolved"] is True

    def test_alerts_combined_filters(self, client, db_session, campaign):
        """severity and resolved filters compose."""
        db_session.add_all([
            Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=AlertSeverity.HIGH,
                message="target",
                metric_value=100.0,
                threshold=50.0,
            ),
            Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=AlertSeverity.HIGH,
                message="wrong-resolved",
                metric_value=100.0,
                threshold=50.0,
                is_resolved=True,
            ),
            Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=AlertSeverity.LOW,
                message="wrong-severity",
                metric_value=10.0,
                threshold=50.0,
            ),
        ])
        db_session.commit()

        data = client.get("/api/v1/dashboard/alerts?severity=high&resolved=false").json()

        assert len(data) == 1
        assert data[0]["message"] == "target"