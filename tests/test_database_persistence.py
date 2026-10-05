"""Comprehensive database persistence tests for all models."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.models.base import Base, TimestampMixin
from app.models.broker import Broker, MENA_COUNTRIES, MENA_CURRENCIES
from app.models.broker_partner import BrokerPartner
from app.models.broker_payout import BrokerPayout, PayoutStatus, PayoutMethod
from app.models.commission_tracking import CommissionTracking, CommissionStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metric import CampaignMetric
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.recommendation import Recommendation, RecommendationCategory


class TestBrokerModel:
    """Tests for Broker model persistence."""

    def test_create_broker_minimal(self, db_session):
        """Create broker with minimal required fields."""
        broker = Broker(name="Test Broker", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        assert broker.id is not None
        assert broker.name == "Test Broker"
        assert broker.country == "AE"
        assert broker.currency == "AED"
        assert float(broker.commission_rate) == 0.05
        assert broker.is_active is True

    def test_create_broker_with_arabic_name(self, db_session):
        """Create broker with Arabic name."""
        broker = Broker(
            name="Dubai Creators Hub",
            name_ar="دبي كرييتورز هب",
            country="AE",
            currency="AED",
            commission_rate=0.05,
        )
        db_session.add(broker)
        db_session.commit()
        assert broker.name_ar == "دبي كرييتورز هب"

    def test_broker_timestamps_auto_set(self, db_session):
        """created_at and updated_at are automatically set."""
        broker = Broker(name="Test", country="SA", currency="SAR", commission_rate=0.03)
        db_session.add(broker)
        db_session.commit()
        assert broker.created_at is not None
        assert broker.updated_at is not None

    def test_broker_repr(self, db_session):
        """Broker repr contains id, name, country."""
        broker = Broker(name="Test Broker", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        repr_str = repr(broker)
        assert "Test Broker" in repr_str
        assert "AE" in repr_str

    def test_broker_all_mena_countries(self, db_session):
        """All MENA countries are accepted."""
        for country in MENA_COUNTRIES:
            broker = Broker(
                name=f"Broker {country}",
                country=country,
                currency="AED",
                commission_rate=0.05,
            )
            db_session.add(broker)
        db_session.commit()
        count = db_session.query(Broker).count()
        assert count == len(MENA_COUNTRIES)

    def test_broker_all_mena_currencies(self, db_session):
        """All MENA currencies are accepted."""
        for currency in MENA_CURRENCIES:
            broker = Broker(
                name=f"Broker {currency}",
                country="AE",
                currency=currency,
                commission_rate=0.05,
            )
            db_session.add(broker)
        db_session.commit()
        count = db_session.query(Broker).count()
        assert count == len(MENA_CURRENCIES)

    def test_broker_commission_rate_zero(self, db_session):
        """Commission rate of 0 is valid."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0)
        db_session.add(broker)
        db_session.commit()
        assert float(broker.commission_rate) == 0.0

    def test_broker_commission_rate_one(self, db_session):
        """Commission rate of 1 is valid."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=1.0)
        db_session.add(broker)
        db_session.commit()
        assert float(broker.commission_rate) == 1.0

    def test_broker_commission_rate_negative_rejected(self, db_session):
        """Negative commission rate is rejected."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=-0.1)
        db_session.add(broker)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_broker_commission_rate_over_one_rejected(self, db_session):
        """Commission rate > 1 is rejected."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=1.5)
        db_session.add(broker)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_broker_invalid_country_rejected(self, db_session):
        """Non-MENA country is rejected."""
        broker = Broker(name="Test", country="US", currency="USD", commission_rate=0.05)
        db_session.add(broker)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_broker_invalid_currency_rejected(self, db_session):
        """Non-MENA currency is rejected."""
        broker = Broker(name="Test", country="AE", currency="USD", commission_rate=0.05)
        db_session.add(broker)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_broker_arabic_name_validation(self, db_session):
        """Arabic name must contain Arabic characters."""
        with pytest.raises(ValueError, match="Arabic name must contain Arabic characters"):
            Broker(
                name="Test",
                name_ar="Not Arabic",
                country="AE",
                currency="AED",
                commission_rate=0.05,
            )

    def test_broker_arabic_name_none_allowed(self, db_session):
        """None Arabic name is allowed."""
        broker = Broker(
            name="Test",
            name_ar=None,
            country="AE",
            currency="AED",
            commission_rate=0.05,
        )
        db_session.add(broker)
        db_session.commit()
        assert broker.name_ar is None

    def test_broker_update(self, db_session):
        """Broker can be updated."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        broker.name = "Updated"
        db_session.commit()
        assert broker.name == "Updated"

    def test_broker_delete(self, db_session):
        """Broker can be deleted."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        broker_id = broker.id
        db_session.delete(broker)
        db_session.commit()
        assert db_session.query(Broker).filter_by(id=broker_id).first() is None

    def test_broker_contact_fields_optional(self, db_session):
        """Contact email and phone are optional."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        assert broker.contact_email is None
        assert broker.contact_phone is None


class TestBrokerPartnerModel:
    """Tests for BrokerPartner model."""

    def test_create_partner(self, db_session):
        """Create a broker partner."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        partner = BrokerPartner(
            broker_id=broker.id,
            partner_name="Partner One",
            partner_name_ar="شريك واحد",
            contact_email="partner@example.com",
            specialization="Real Estate",
        )
        db_session.add(partner)
        db_session.commit()
        assert partner.id is not None
        assert partner.broker_id == broker.id
        assert partner.partner_name == "Partner One"
        assert partner.is_active is True

    def test_partner_cascade_delete(self, db_session):
        """Deleting broker cascades to partners."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        partner = BrokerPartner(broker_id=broker.id, partner_name="Partner")
        db_session.add(partner)
        db_session.commit()
        broker_id = broker.id
        db_session.delete(broker)
        db_session.commit()
        assert db_session.query(BrokerPartner).filter_by(broker_id=broker_id).first() is None

    def test_partner_broker_relationship(self, db_session):
        """Partner has broker relationship."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        partner = BrokerPartner(broker_id=broker.id, partner_name="Partner")
        db_session.add(partner)
        db_session.commit()
        assert partner.broker.name == "Test"

    def test_broker_partners_relationship(self, db_session):
        """Broker has partners relationship."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        p1 = BrokerPartner(broker_id=broker.id, partner_name="P1")
        p2 = BrokerPartner(broker_id=broker.id, partner_name="P2")
        db_session.add_all([p1, p2])
        db_session.commit()
        assert len(broker.partners) == 2


class TestCommissionTrackingModel:
    """Tests for CommissionTracking model."""

    def test_create_commission(self, db_session):
        """Create a commission record."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        commission = CommissionTracking(
            broker_id=broker.id,
            deal_id="DEAL-001",
            deal_amount=10000.00,
            commission_rate=0.05,
            commission_amount=500.00,
            currency="AED",
            deal_date=date(2024, 1, 15),
        )
        db_session.add(commission)
        db_session.commit()
        assert commission.id is not None
        assert commission.status == CommissionStatus.PENDING

    def test_commission_status_transitions(self, db_session):
        """Commission status can be updated."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        commission = CommissionTracking(
            broker_id=broker.id,
            deal_id="DEAL-001",
            deal_amount=10000.00,
            commission_rate=0.05,
            commission_amount=500.00,
            currency="AED",
            deal_date=date(2024, 1, 15),
        )
        db_session.add(commission)
        db_session.commit()
        commission.status = CommissionStatus.APPROVED
        db_session.commit()
        assert commission.status == CommissionStatus.APPROVED

    def test_commission_all_statuses(self, db_session):
        """All commission statuses are valid."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        for status in CommissionStatus:
            commission = CommissionTracking(
                broker_id=broker.id,
                deal_id=f"DEAL-{status.value}",
                deal_amount=1000.00,
                commission_rate=0.05,
                commission_amount=50.00,
                currency="AED",
                deal_date=date(2024, 1, 15),
                status=status,
            )
            db_session.add(commission)
        db_session.commit()
        count = db_session.query(CommissionTracking).count()
        assert count == len(CommissionStatus)

    def test_commission_cascade_delete(self, db_session):
        """Deleting broker cascades to commissions."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        commission = CommissionTracking(
            broker_id=broker.id,
            deal_id="DEAL-001",
            deal_amount=10000.00,
            commission_rate=0.05,
            commission_amount=500.00,
            currency="AED",
            deal_date=date(2024, 1, 15),
        )
        db_session.add(commission)
        db_session.commit()
        broker_id = broker.id
        db_session.delete(broker)
        db_session.commit()
        assert db_session.query(CommissionTracking).filter_by(broker_id=broker_id).first() is None


class TestBrokerPayoutModel:
    """Tests for BrokerPayout model."""

    def test_create_payout(self, db_session):
        """Create a payout record."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        payout = BrokerPayout(
            broker_id=broker.id,
            amount=5000.00,
            currency="AED",
            payout_method=PayoutMethod.BANK_TRANSFER,
            reference_number="PAY-001",
            bank_name="Emirates NBD",
            bank_account_last4="1234",
            iban="AE070331234567890123456",
            scheduled_date=date(2024, 3, 1),
        )
        db_session.add(payout)
        db_session.commit()
        assert payout.id is not None
        assert payout.status == PayoutStatus.SCHEDULED

    def test_payout_all_methods(self, db_session):
        """All payout methods are valid."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        for method in PayoutMethod:
            payout = BrokerPayout(
                broker_id=broker.id,
                amount=1000.00,
                currency="AED",
                payout_method=method,
            )
            db_session.add(payout)
        db_session.commit()
        count = db_session.query(BrokerPayout).count()
        assert count == len(PayoutMethod)

    def test_payout_all_statuses(self, db_session):
        """All payout statuses are valid."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        for status in PayoutStatus:
            payout = BrokerPayout(
                broker_id=broker.id,
                amount=1000.00,
                currency="AED",
                payout_method=PayoutMethod.BANK_TRANSFER,
                status=status,
            )
            db_session.add(payout)
        db_session.commit()
        count = db_session.query(BrokerPayout).count()
        assert count == len(PayoutStatus)

    def test_payout_cascade_delete(self, db_session):
        """Deleting broker cascades to payouts."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        payout = BrokerPayout(
            broker_id=broker.id,
            amount=1000.00,
            currency="AED",
            payout_method=PayoutMethod.BANK_TRANSFER,
        )
        db_session.add(payout)
        db_session.commit()
        broker_id = broker.id
        db_session.delete(broker)
        db_session.commit()
        assert db_session.query(BrokerPayout).filter_by(broker_id=broker_id).first() is None


class TestCampaignModel:
    """Tests for Campaign model."""

    def test_create_campaign(self, db_session):
        """Create a campaign."""
        campaign = Campaign(
            name="Test Campaign",
            description="A test campaign",
            status=CampaignStatus.ACTIVE,
            budget=10000.00,
            spent=5000.00,
            target_roas=2.0,
            target_ctr=0.01,
        )
        db_session.add(campaign)
        db_session.commit()
        assert campaign.id is not None
        assert campaign.name == "Test Campaign"
        assert campaign.status == CampaignStatus.ACTIVE

    def test_campaign_all_statuses(self, db_session):
        """All campaign statuses are valid."""
        for status in CampaignStatus:
            campaign = Campaign(
                name=f"Campaign {status.value}",
                status=status,
                budget=1000.00,
            )
            db_session.add(campaign)
        db_session.commit()
        count = db_session.query(Campaign).count()
        assert count == len(CampaignStatus)

    def test_campaign_timestamps(self, db_session):
        """Campaign has timestamps."""
        campaign = Campaign(name="Test", status=CampaignStatus.DRAFT, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        assert campaign.created_at is not None
        assert campaign.updated_at is not None


class TestCampaignMetricModel:
    """Tests for CampaignMetric model."""

    def test_create_metric(self, db_session):
        """Create a campaign metric."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
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
        assert metric.id is not None
        assert metric.impressions == 10000
        assert metric.clicks == 100

    def test_metric_cascade_delete(self, db_session):
        """Deleting campaign cascades to metrics."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        metric = CampaignMetric(campaign_id=campaign.id, impressions=100)
        db_session.add(metric)
        db_session.commit()
        campaign_id = campaign.id
        db_session.delete(campaign)
        db_session.commit()
        assert db_session.query(CampaignMetric).filter_by(campaign_id=campaign_id).first() is None


class TestAlertModel:
    """Tests for Alert model."""

    def test_create_alert(self, db_session):
        """Create an alert."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        alert = Alert(
            campaign_id=campaign.id,
            alert_type=AlertType.SPEND_SPIKE,
            severity=AlertSeverity.HIGH,
            message="Spend spike detected",
            metric_value=5000.00,
            threshold=2000.00,
        )
        db_session.add(alert)
        db_session.commit()
        assert alert.id is not None
        assert alert.is_resolved is False

    def test_alert_all_types(self, db_session):
        """All alert types are valid."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        for alert_type in AlertType:
            alert = Alert(
                campaign_id=campaign.id,
                alert_type=alert_type,
                severity=AlertSeverity.MEDIUM,
                message=f"Alert {alert_type.value}",
                metric_value=100.00,
                threshold=50.00,
            )
            db_session.add(alert)
        db_session.commit()
        count = db_session.query(Alert).count()
        assert count == len(AlertType)

    def test_alert_all_severities(self, db_session):
        """All alert severities are valid."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        for severity in AlertSeverity:
            alert = Alert(
                campaign_id=campaign.id,
                alert_type=AlertType.SPEND_SPIKE,
                severity=severity,
                message=f"Alert {severity.value}",
                metric_value=100.00,
                threshold=50.00,
            )
            db_session.add(alert)
        db_session.commit()
        count = db_session.query(Alert).count()
        assert count == len(AlertSeverity)


class TestRecommendationModel:
    """Tests for Recommendation model."""

    def test_create_recommendation(self, db_session):
        """Create a recommendation."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        rec = Recommendation(
            campaign_id=campaign.id,
            category=RecommendationCategory.BUDGET_REALLOCATION,
            priority=1,
            title="Reallocate budget",
            description="Shift budget to better performing ads",
            expected_impact=0.15,
        )
        db_session.add(rec)
        db_session.commit()
        assert rec.id is not None
        assert rec.is_applied is False

    def test_recommendation_all_categories(self, db_session):
        """All recommendation categories are valid."""
        campaign = Campaign(name="Test", status=CampaignStatus.ACTIVE, budget=1000.00)
        db_session.add(campaign)
        db_session.commit()
        for category in RecommendationCategory:
            rec = Recommendation(
                campaign_id=campaign.id,
                category=category,
                priority=5,
                title=f"Rec {category.value}",
                description="Test recommendation",
                expected_impact=0.1,
            )
            db_session.add(rec)
        db_session.commit()
        count = db_session.query(Recommendation).count()
        assert count == len(RecommendationCategory)


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_mixin_provides_timestamps(self, db_session):
        """TimestampMixin provides created_at and updated_at."""
        broker = Broker(name="Test", country="AE", currency="AED", commission_rate=0.05)
        db_session.add(broker)
        db_session.commit()
        assert hasattr(broker, "created_at")
        assert hasattr(broker, "updated_at")
        assert broker.created_at is not None
        assert broker.updated_at is not None
