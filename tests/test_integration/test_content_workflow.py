"""Integration tests spanning multiple broker/campaign resources.

These exercise real cross-resource flows through the HTTP API using the
``client`` fixture (get_db is overridden to the per-test in-memory database).

Only routes that actually exist in ``app/`` are used — the campaign/alert
resources have no create endpoint, so those rows are seeded via ``db_session``.
"""
from datetime import date
from decimal import Decimal

import pytest

from app import models  # noqa: F401
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.campaign import Campaign, CampaignStatus


@pytest.fixture
def campaign(db_session):
    """An active campaign seeded directly (no create endpoint exists)."""
    obj = Campaign(
        name="Integration Campaign",
        description="Seeded for integration tests",
        status=CampaignStatus.ACTIVE,
        budget=10000.00,
        spent=0.0,
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


class TestBrokerOnboardingWorkflow:
    """Broker registration then first deal onboarding."""

    def test_broker_to_first_commission(self, client, sample_broker, sample_commission_data):
        """A new broker can immediately record and list its first commission."""
        assert client.get("/api/v1/commissions").json() == []

        created = client.post("/api/v1/commissions", json=sample_commission_data)
        assert created.status_code == 201
        assert created.json()["deal_id"] == "DEAL-001"

        listed = client.get("/api/v1/commissions", params={"broker_id": sample_broker["id"]})
        assert listed.status_code == 200
        assert len(listed.json()) == 1

    def test_commission_filtered_by_other_broker_is_empty(self, client, sample_broker, sample_broker_data):
        """Commission filtering is scoped to the requested broker."""
        other_data = dict(sample_broker_data, name="Other Broker", name_ar="آخر", email="other@example.com")
        other = client.post("/api/v1/brokers", json=other_data).json()

        assert client.get("/api/v1/commissions", params={"broker_id": other["id"]}).json() == []

    def test_broker_lifecycle(self, client, sample_broker):
        """Create, read, update and delete a broker through the API."""
        broker_id = sample_broker["id"]

        assert client.get(f"/api/v1/brokers/{broker_id}").json()["id"] == broker_id

        updated = client.put(f"/api/v1/brokers/{broker_id}", json={
            "name": "Renamed Broker",
            "name_ar": "وسيط",
            "country": "SA",
            "currency": "SAR",
            "commission_rate": 0.07,
            "contact_email": "renamed@example.com",
            "contact_phone": "+966500000000",
            "is_active": True,
        })
        assert updated.status_code == 200
        data = updated.json()
        assert data["country"] == "SA"
        # Decimal fields serialize as JSON strings
        assert data["commission_rate"] == "0.0700"

        assert client.delete(f"/api/v1/brokers/{broker_id}").status_code == 204
        assert client.get(f"/api/v1/brokers/{broker_id}").status_code == 404

    def test_broker_update_is_partial(self, client, sample_broker):
        """BrokerUpdate fields are optional; omitted fields are untouched."""
        broker_id = sample_broker["id"]

        response = client.put(f"/api/v1/brokers/{broker_id}", json={"country": "EG"})

        assert response.status_code == 200
        data = response.json()
        assert data["country"] == "EG"
        assert data["name"] == sample_broker["name"]
        assert data["currency"] == sample_broker["currency"]


class TestCommissionCalculationWorkflow:
    """The calculate endpoint derives commission from the broker's rate."""

    def test_calculate_uses_broker_rate(self, client, sample_broker):
        """Commission = deal_amount * broker.commission_rate.

        Decimal fields are serialized as JSON strings by the response model.
        """
        response = client.post("/api/v1/commissions/calculate", json={
            "broker_id": sample_broker["id"],
            "deal_amount": "20000.00",
            "currency": "AED",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["commission_rate"] == "0.0500"
        assert Decimal(data["commission_amount"]) == Decimal("1000.00")

    def test_calculate_unknown_broker_returns_404(self, client):
        response = client.post("/api/v1/commissions/calculate", json={
            "broker_id": 9999,
            "deal_amount": 100.0,
            "currency": "AED",
        })

        assert response.status_code == 404
        assert response.json()["detail"] == "Broker not found"

    def test_calculated_amount_can_be_recorded(self, client, sample_broker, sample_commission_data):
        """The calculated figure round-trips into a stored commission."""
        calculated = client.post("/api/v1/commissions/calculate", json={
            "broker_id": sample_broker["id"],
            "deal_amount": str(sample_commission_data["deal_amount"]),
            "currency": sample_commission_data["currency"],
        }).json()

        sample_commission_data["commission_amount"] = calculated["commission_amount"]
        stored = client.post("/api/v1/commissions", json=sample_commission_data)

        assert stored.status_code == 201
        assert Decimal(stored.json()["commission_amount"]) == Decimal(
            calculated["commission_amount"]
        )


class TestCommissionStatusWorkflow:
    """Commissions progress from pending through to paid."""

    def test_status_transitions(self, client, sample_broker, sample_commission_data):
        """A commission can be advanced through its lifecycle."""
        created = client.post("/api/v1/commissions", json=sample_commission_data).json()
        commission_id = created["id"]
        assert created["status"] == "pending"

        for status in ("approved", "paid"):
            response = client.patch(
                f"/api/v1/commissions/{commission_id}/status", json={"status": status}
            )
            assert response.status_code == 200
            assert response.json()["status"] == status

    def test_unknown_commission_status_update_returns_404(self, client):
        response = client.patch("/api/v1/commissions/9999/status", json={"status": "paid"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Commission not found"


class TestPayoutWorkflow:
    """Payout scheduling and status progression."""

    def test_payout_lifecycle(self, client, sample_broker, sample_payout_data):
        """A payout is created, listed, advanced and summarised."""
        created = client.post("/api/v1/payouts", json=sample_payout_data)
        assert created.status_code == 201
        payout_id = created.json()["id"]

        assert len(client.get("/api/v1/payouts").json()) == 1

        updated = client.patch(f"/api/v1/payouts/{payout_id}/status", json={"status": "processing"})
        assert updated.status_code == 200
        assert updated.json()["status"] == "processing"

        # /payouts/summary is scoped per broker — broker_id is required
        summary = client.get(
            "/api/v1/payouts/summary", params={"broker_id": sample_broker["id"]}
        )
        assert summary.status_code == 200
        assert Decimal(summary.json()["total_amount"]) == Decimal("5000.00")
        assert summary.json()["count"] == 1

    def test_payout_summary_requires_broker_id(self, client):
        """broker_id is a required query parameter, so omitting it is a 422."""
        assert client.get("/api/v1/payouts/summary").status_code == 422

    def test_payout_amount_reflected_in_broker_dashboard(self, client, sample_broker, sample_payout_data):
        """A recorded payout shows up in the broker's dashboard totals."""
        client.post("/api/v1/payouts", json=sample_payout_data)

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["payouts"]["total_count"] == 1
        assert data["payouts"]["total_amount"] == 5000.00

    def test_unknown_payout_status_update_returns_404(self, client):
        response = client.patch("/api/v1/payouts/9999/status", json={"status": "processing"})

        assert response.status_code == 404


class TestCampaignAnalyticsWorkflow:
    """Campaign metrics ingested over the API feed the dashboards."""

    def test_ingest_metric_then_read_it_back(self, client, campaign):
        """A posted metric is retrievable from the campaign's metric list."""
        posted = client.post(f"/api/campaigns/{campaign.id}/metrics", json={
            "impressions": 5000,
            "clicks": 50,
            "conversions": 5,
            "spend": 250.0,
            "revenue": 500.0,
        })
        assert posted.status_code == 201

        metrics = client.get(f"/api/campaigns/{campaign.id}/metrics")
        assert metrics.status_code == 200
        assert len(metrics.json()) == 1
        assert metrics.json()[0]["impressions"] == 5000

    def test_metric_ingest_updates_performance_dashboard(self, client, campaign):
        """Ingested metrics drive the dashboard's ctr/roas calculations."""
        client.post(f"/api/campaigns/{campaign.id}/metrics", json={
            "impressions": 10000,
            "clicks": 100,
            "conversions": 10,
            "spend": 500.0,
            "revenue": 1000.0,
        })

        performance = client.get(f"/api/v1/dashboard/campaigns/{campaign.id}/performance").json()

        assert performance["metrics"]["total_impressions"] == 10000
        assert performance["metrics"]["ctr"] == 0.01
        assert performance["metrics"]["roas"] == 2.0

    def test_metric_ingest_updates_campaign_summary(self, client, campaign):
        """Aggregated spend/revenue appear on the campaign listing."""
        client.post(f"/api/campaigns/{campaign.id}/metrics", json={
            "impressions": 100,
            "clicks": 10,
            "conversions": 1,
            "spend": 40.0,
            "revenue": 100.0,
        })

        summary = client.get(f"/api/campaigns/{campaign.id}").json()

        assert summary["total_spend"] == pytest.approx(40.0)
        assert summary["total_revenue"] == pytest.approx(100.0)

    def test_metric_ingest_for_unknown_campaign_returns_404(self, client):
        response = client.post("/api/campaigns/9999/metrics", json={
            "impressions": 1, "clicks": 1, "conversions": 0, "spend": 1.0, "revenue": 1.0,
        })

        assert response.status_code == 404

    def test_campaigns_listing_includes_seeded_campaign(self, client, campaign):
        response = client.get("/api/campaigns")

        assert response.status_code == 200
        assert any(c["id"] == campaign.id for c in response.json())


class TestAlertResolutionWorkflow:
    """Alerts are surfaced, filtered and resolved."""

    @pytest.fixture
    def alert(self, db_session, campaign):
        obj = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="Spend spiked",
            metric_value=500.0,
            threshold=100.0,
        )
        db_session.add(obj)
        db_session.commit()
        db_session.refresh(obj)
        return obj

    def test_alert_listed_for_campaign(self, client, alert):
        response = client.get(f"/api/campaigns/{alert.campaign_id}/alerts")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["severity"] == "high"

    def test_resolving_alert_clears_it_from_unresolved_views(self, client, alert):
        """Resolution removes the alert from the unresolved dashboard counter."""
        assert client.get("/api/v1/dashboard/summary").json()["alerts"]["unresolved"] == 1

        resolved = client.post(f"/api/alerts/{alert.id}/resolve")
        assert resolved.status_code == 200
        assert resolved.json()["is_resolved"] is True

        assert client.get("/api/v1/dashboard/summary").json()["alerts"]["unresolved"] == 0
        assert client.get("/api/v1/dashboard/alerts?resolved=false").json() == []

    def test_resolving_unknown_alert_returns_404(self, client):
        assert client.post("/api/alerts/9999/resolve").status_code == 404

    def test_alerts_for_unknown_campaign_returns_404(self, client):
        assert client.get("/api/campaigns/9999/alerts").status_code == 404


class TestHealthAndDashboardConsistency:
    """The health endpoint and the two dashboard views stay consistent."""

    def test_health_endpoint(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_broker_dashboard_reflects_commissions_and_payouts(
        self, client, sample_broker, sample_commission_data, sample_payout_data
    ):
        """Both resource types aggregate into the per-broker dashboard."""
        client.post("/api/v1/commissions", json=sample_commission_data)
        client.post("/api/v1/payouts", json=sample_payout_data)

        data = client.get(f"/api/v1/dashboard/broker/{sample_broker['id']}").json()

        assert data["broker"]["id"] == sample_broker["id"]
        assert data["commissions"]["total_count"] == 1
        assert data["commissions"]["total_amount"] == 500.00
        assert data["payouts"]["total_count"] == 1
        assert data["payouts"]["total_amount"] == 5000.00

    def test_summary_counts_match_listed_resources(self, client, sample_broker, sample_commission_data):
        """Dashboard summary totals agree with the underlying list endpoints."""
        client.post("/api/v1/commissions", json=sample_commission_data)

        summary = client.get("/api/v1/dashboard/summary").json()
        brokers = client.get("/api/v1/brokers").json()
        commissions = client.get("/api/v1/commissions").json()

        assert summary["brokers"]["total"] == len(brokers)
        assert summary["commissions"]["total"] == len(commissions)

    def test_unknown_resources_return_404_across_dashboards(self, client):
        """Every dashboard 404s cleanly for missing ids."""
        assert client.get("/api/v1/dashboard/broker/9999").status_code == 404
        assert client.get("/api/v1/dashboard/campaigns/9999/performance").status_code == 404