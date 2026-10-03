"""Comprehensive agent tests for creator monetization functions.

Tests cover:
- calculate_payout: revenue share calculation for creators
- get_monetization_tier: tier determination based on earnings/engagement
- process_payout: end-to-end payout processing workflow
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

from ugc_marketplace.agents.creator_monetization import (
    calculate_payout,
    get_monetization_tier,
    process_payout,
    PayoutStatus,
    MonetizationTier,
    PayoutError,
    InsufficientFundsError,
    CreatorNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def creator_id():
    """Return a valid creator UUID."""
    return uuid4()


@pytest.fixture
def content_id():
    """Return a valid content UUID."""
    return uuid4()


@pytest.fixture
def sample_creator(creator_id):
    """Return a sample creator profile dict."""
    return {
        "id": creator_id,
        "username": "test_creator",
        "email": "creator@example.com",
        "total_earnings": Decimal("500.00"),
        "pending_payout": Decimal("0.00"),
        "tier": "bronze",
        "payout_method": "bank_transfer",
        "payout_details": {"account_number": "****1234", "routing": "****5678"},
        "is_active": True,
        "created_at": datetime(2024, 1, 1),
    }


@pytest.fixture
def sample_content(content_id, creator_id):
    """Return a sample content item dict."""
    return {
        "id": content_id,
        "creator_id": creator_id,
        "title": "Test Content",
        "type": "video",
        "views": 10000,
        "likes": 500,
        "revenue": Decimal("100.00"),
        "status": "published",
        "created_at": datetime(2024, 6, 1),
    }


@pytest.fixture
def mock_db():
    """Return a mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


@pytest.fixture
def mock_payout_gateway():
    """Return a mock payment gateway."""
    gateway = MagicMock()
    gateway.process_payment.return_value = {
        "transaction_id": str(uuid4()),
        "status": "completed",
        "amount": Decimal("100.00"),
        "processed_at": datetime.utcnow(),
    }
    return gateway


@pytest.fixture
def mock_notification_service():
    """Return a mock notification service."""
    service = MagicMock()
    service.send_notification.return_value = True
    return service


@pytest.fixture
def bronze_tier_config():
    """Return bronze tier configuration."""
    return {
        "name": "bronze",
        "min_earnings": Decimal("0"),
        "max_earnings": Decimal("999.99"),
        "revenue_share": Decimal("0.50"),
        "payout_threshold": Decimal("50.00"),
        "payout_frequency": "monthly",
    }


@pytest.fixture
def silver_tier_config():
    """Return silver tier configuration."""
    return {
        "name": "silver",
        "min_earnings": Decimal("1000.00"),
        "max_earnings": Decimal("4999.99"),
        "revenue_share": Decimal("0.60"),
        "payout_threshold": Decimal("100.00"),
        "payout_frequency": "bi_weekly",
    }


@pytest.fixture
def gold_tier_config():
    """Return gold tier configuration."""
    return {
        "name": "gold",
        "min_earnings": Decimal("5000.00"),
        "max_earnings": Decimal("19999.99"),
        "revenue_share": Decimal("0.70"),
        "payout_threshold": Decimal("250.00"),
        "payout_frequency": "weekly",
    }


@pytest.fixture
def platinum_tier_config():
    """Return platinum tier configuration."""
    return {
        "name": "platinum",
        "min_earnings": Decimal("20000.00"),
        "max_earnings": Decimal("999999999.99"),
        "revenue_share": Decimal("0.80"),
        "payout_threshold": Decimal("500.00"),
        "payout_frequency": "weekly",
    }


@pytest.fixture
def all_tier_configs(
    bronze_tier_config, silver_tier_config, gold_tier_config, platinum_tier_config
):
    """Return all tier configurations."""
    return [
        bronze_tier_config,
        silver_tier_config,
        gold_tier_config,
        platinum_tier_config,
    ]


# ---------------------------------------------------------------------------
# Tests for calculate_payout
# ---------------------------------------------------------------------------


class TestCalculatePayout:
    """Test suite for calculate_payout function."""

    def test_calculate_payout_basic(self, creator_id, content_id):
        """Test basic payout calculation with standard inputs."""
        revenue = Decimal("100.00")
        revenue_share = Decimal("0.50")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=revenue_share,
        )

        assert result["creator_id"] == creator_id
        assert result["content_id"] == content_id
        assert result["gross_revenue"] == revenue
        assert result["revenue_share"] == revenue_share
        assert result["payout_amount"] == Decimal("50.00")
        assert result["platform_fee"] == Decimal("50.00")
        assert result["currency"] == "USD"

    def test_calculate_payout_zero_revenue(self, creator_id, content_id):
        """Test payout calculation with zero revenue."""
        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=Decimal("0.00"),
            revenue_share=Decimal("0.50"),
        )

        assert result["payout_amount"] == Decimal("0.00")
        assert result["platform_fee"] == Decimal("0.00")

    def test_calculate_payout_full_share(self, creator_id, content_id):
        """Test payout calculation with 100% revenue share."""
        revenue = Decimal("200.00")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=Decimal("1.00"),
        )

        assert result["payout_amount"] == Decimal("200.00")
        assert result["platform_fee"] == Decimal("0.00")

    def test_calculate_payout_zero_share(self, creator_id, content_id):
        """Test payout calculation with 0% revenue share."""
        revenue = Decimal("200.00")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=Decimal("0.00"),
        )

        assert result["payout_amount"] == Decimal("0.00")
        assert result["platform_fee"] == Decimal("200.00")

    def test_calculate_payout_fractional_amounts(self, creator_id, content_id):
        """Test payout calculation with fractional amounts."""
        revenue = Decimal("33.33")
        revenue_share = Decimal("0.65")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=revenue_share,
        )

        expected_payout = (revenue * revenue_share).quantize(Decimal("0.01"))
        expected_fee = (revenue - expected_payout).quantize(Decimal("0.01"))

        assert result["payout_amount"] == expected_payout
        assert result["platform_fee"] == expected_fee

    def test_calculate_payout_large_revenue(self, creator_id, content_id):
        """Test payout calculation with large revenue amounts."""
        revenue = Decimal("1000000.00")
        revenue_share = Decimal("0.80")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=revenue_share,
        )

        assert result["payout_amount"] == Decimal("800000.00")
        assert result["platform_fee"] == Decimal("200000.00")

    def test_calculate_payout_preserves_precision(self, creator_id, content_id):
        """Test that payout calculation preserves decimal precision."""
        revenue = Decimal("99.99")
        revenue_share = Decimal("0.333")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=revenue_share,
        )

        # Verify the result has proper decimal precision
        assert isinstance(result["payout_amount"], Decimal)
        assert isinstance(result["platform_fee"], Decimal)
        # Payout + fee should equal revenue (within rounding)
        total = result["payout_amount"] + result["platform_fee"]
        assert abs(total - revenue) <= Decimal("0.01")

    def test_calculate_payout_with_custom_currency(self, creator_id, content_id):
        """Test payout calculation with custom currency."""
        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=Decimal("100.00"),
            revenue_share=Decimal("0.50"),
            currency="EUR",
        )

        assert result["currency"] == "EUR"

    def test_calculate_payout_returns_dict(self, creator_id, content_id):
        """Test that calculate_payout returns a dictionary."""
        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=Decimal("100.00"),
            revenue_share=Decimal("0.50"),
        )

        assert isinstance(result, dict)
        assert "creator_id" in result
        assert "content_id" in result
        assert "gross_revenue" in result
        assert "payout_amount" in result
        assert "platform_fee" in result
        assert "currency" in result

    def test_calculate_payout_negative_revenue_raises_error(
        self, creator_id, content_id
    ):
        """Test that negative revenue raises an error."""
        with pytest.raises(ValueError, match="Revenue cannot be negative"):
            calculate_payout(
                creator_id=creator_id,
                content_id=content_id,
                revenue=Decimal("-10.00"),
                revenue_share=Decimal("0.50"),
            )

    def test_calculate_payout_invalid_share_raises_error(self, creator_id, content_id):
        """Test that revenue share > 1.0 raises an error."""
        with pytest.raises(ValueError, match="Revenue share must be between 0 and 1"):
            calculate_payout(
                creator_id=creator_id,
                content_id=content_id,
                revenue=Decimal("100.00"),
                revenue_share=Decimal("1.50"),
            )

    def test_calculate_payout_negative_share_raises_error(self, creator_id, content_id):
        """Test that negative revenue share raises an error."""
        with pytest.raises(ValueError, match="Revenue share must be between 0 and 1"):
            calculate_payout(
                creator_id=creator_id,
                content_id=content_id,
                revenue=Decimal("100.00"),
                revenue_share=Decimal("-0.10"),
            )

    def test_calculate_payout_very_small_revenue(self, creator_id, content_id):
        """Test payout calculation with very small revenue."""
        revenue = Decimal("0.01")
        revenue_share = Decimal("0.50")

        result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=revenue_share,
        )

        assert result["payout_amount"] == Decimal("0.01")  # Rounded
        assert result["platform_fee"] == Decimal("0.00")  # Rounded


# ---------------------------------------------------------------------------
# Tests for get_monetization_tier
# ---------------------------------------------------------------------------


class TestGetMonetizationTier:
    """Test suite for get_monetization_tier function."""

    def test_get_monetization_tier_bronze(self, all_tier_configs):
        """Test tier determination for bronze level earnings."""
        total_earnings = Decimal("500.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "bronze"
        assert result["revenue_share"] == Decimal("0.50")
        assert result["payout_threshold"] == Decimal("50.00")

    def test_get_monetization_tier_silver(self, all_tier_configs):
        """Test tier determination for silver level earnings."""
        total_earnings = Decimal("2500.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "silver"
        assert result["revenue_share"] == Decimal("0.60")
        assert result["payout_threshold"] == Decimal("100.00")

    def test_get_monetization_tier_gold(self, all_tier_configs):
        """Test tier determination for gold level earnings."""
        total_earnings = Decimal("10000.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "gold"
        assert result["revenue_share"] == Decimal("0.70")
        assert result["payout_threshold"] == Decimal("250.00")

    def test_get_monetization_tier_platinum(self, all_tier_configs):
        """Test tier determination for platinum level earnings."""
        total_earnings = Decimal("50000.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "platinum"
        assert result["revenue_share"] == Decimal("0.80")
        assert result["payout_threshold"] == Decimal("500.00")

    def test_get_monetization_tier_boundary_bronze_silver(self, all_tier_configs):
        """Test tier at bronze/silver boundary."""
        total_earnings = Decimal("999.99")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "bronze"

    def test_get_monetization_tier_boundary_silver_start(self, all_tier_configs):
        """Test tier at silver start boundary."""
        total_earnings = Decimal("1000.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "silver"

    def test_get_monetization_tier_boundary_silver_gold(self, all_tier_configs):
        """Test tier at silver/gold boundary."""
        total_earnings = Decimal("4999.99")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "silver"

    def test_get_monetization_tier_boundary_gold_start(self, all_tier_configs):
        """Test tier at gold start boundary."""
        total_earnings = Decimal("5000.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "gold"

    def test_get_monetization_tier_boundary_gold_platinum(self, all_tier_configs):
        """Test tier at gold/platinum boundary."""
        total_earnings = Decimal("19999.99")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "gold"

    def test_get_monetization_tier_boundary_platinum_start(self, all_tier_configs):
        """Test tier at platinum start boundary."""
        total_earnings = Decimal("20000.00")

        result = get_monetization_tier(
            total_earnings=total_earnings,
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "platinum"

    def test_get_monetization_tier_zero_earnings(self, all_tier_configs):
        """Test tier determination with zero earnings."""
        result = get_monetization_tier(
            total_earnings=Decimal("0.00"),
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "bronze"

    def test_get_monetization_tier_very_high_earnings(self, all_tier_configs):
        """Test tier determination with very high earnings."""
        result = get_monetization_tier(
            total_earnings=Decimal("999999.99"),
            tier_configs=all_tier_configs,
        )

        assert result["tier"] == "platinum"

    def test_get_monetization_tier_returns_dict(self, all_tier_configs):
        """Test that get_monetization_tier returns a dictionary."""
        result = get_monetization_tier(
            total_earnings=Decimal("1000.00"),
            tier_configs=all_tier_configs,
        )

        assert isinstance(result, dict)
        assert "tier" in result
        assert "revenue_share" in result
        assert "payout_threshold" in result
        assert "payout_frequency" in result

    def test_get_monetization_tier_negative_earnings_raises_error(
        self, all_tier_configs
    ):
        """Test that negative earnings raises an error."""
        with pytest.raises(ValueError, match="Total earnings cannot be negative"):
            get_monetization_tier(
                total_earnings=Decimal("-100.00"),
                tier_configs=all_tier_configs,
            )

    def test_get_monetization_tier_empty_configs_raises_error(self):
        """Test that empty tier configs raises an error."""
        with pytest.raises(ValueError, match="Tier configs cannot be empty"):
            get_monetization_tier(
                total_earnings=Decimal("1000.00"),
                tier_configs=[],
            )

    def test_get_monetization_tier_includes_next_tier_info(self, all_tier_configs):
        """Test that result includes next tier information."""
        result = get_monetization_tier(
            total_earnings=Decimal("500.00"),
            tier_configs=all_tier_configs,
        )

        assert "next_tier" in result
        assert result["next_tier"]["name"] == "silver"
        assert result["next_tier"]["min_earnings"] == Decimal("1000.00")

    def test_get_monetization_tier_top_tier_no_next(self, all_tier_configs):
        """Test that top tier has no next tier."""
        result = get_monetization_tier(
            total_earnings=Decimal("50000.00"),
            tier_configs=all_tier_configs,
        )

        assert result["next_tier"] is None

    def test_get_monetization_tier_progress_to_next(self, all_tier_configs):
        """Test progress calculation to next tier."""
        result = get_monetization_tier(
            total_earnings=Decimal("750.00"),
            tier_configs=all_tier_configs,
        )

        assert "progress_to_next" in result
        # 750 out of 1000 needed for silver = 75%
        assert result["progress_to_next"] == Decimal("75.00")


# ---------------------------------------------------------------------------
# Tests for process_payout
# ---------------------------------------------------------------------------


class TestProcessPayout:
    """Test suite for process_payout function."""

    def test_process_payout_success(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test successful payout processing."""
        payout_amount = Decimal("100.00")

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert result["status"] == PayoutStatus.COMPLETED
        assert result["creator_id"] == creator_id
        assert result["amount"] == payout_amount
        assert "transaction_id" in result
        assert "processed_at" in result

    def test_process_payout_updates_creator_balance(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test that payout processing updates creator balance."""
        payout_amount = Decimal("100.00")
        original_earnings = sample_creator["total_earnings"]

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        # Verify database was updated
        mock_db.commit.assert_called_once()

    def test_process_payout_sends_notification(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test that payout processing sends notification to creator."""
        payout_amount = Decimal("100.00")

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args
        assert call_args[1]["creator_id"] == creator_id
        assert call_args[1]["amount"] == payout_amount

    def test_process_payout_below_threshold(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing when amount is below threshold."""
        payout_amount = Decimal("10.00")  # Below $50 threshold

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert result["status"] == PayoutStatus.PENDING
        assert result["reason"] == "below_threshold"

    def test_process_payout_creator_not_found(
        self, creator_id, mock_db, mock_payout_gateway, mock_notification_service
    ):
        """Test payout processing when creator is not found."""
        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=None,
        ):
            with pytest.raises(CreatorNotFoundError):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("100.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_insufficient_funds(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with insufficient creator balance."""
        sample_creator["total_earnings"] = Decimal("50.00")

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            with pytest.raises(InsufficientFundsError):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("100.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_gateway_failure(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing when payment gateway fails."""
        mock_payout_gateway.process_payment.side_effect = Exception(
            "Gateway timeout"
        )

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=Decimal("100.00"),
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert result["status"] == PayoutStatus.FAILED
        assert "error" in result
        mock_db.rollback.assert_called_once()

    def test_process_payout_inactive_creator(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing for inactive creator."""
        sample_creator["is_active"] = False

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            with pytest.raises(PayoutError, match="Creator account is not active"):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("100.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_no_payout_method(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing when creator has no payout method."""
        sample_creator["payout_method"] = None

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            with pytest.raises(PayoutError, match="No payout method configured"):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("100.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_zero_amount(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with zero amount."""
        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            with pytest.raises(ValueError, match="Payout amount must be positive"):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("0.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_negative_amount(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with negative amount."""
        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            with pytest.raises(ValueError, match="Payout amount must be positive"):
                process_payout(
                    creator_id=creator_id,
                    amount=Decimal("-50.00"),
                    db=mock_db,
                    payout_gateway=mock_payout_gateway,
                    notification_service=mock_notification_service,
                )

    def test_process_payout_exact_threshold(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing at exact threshold amount."""
        payout_amount = Decimal("50.00")  # Exact threshold

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert result["status"] == PayoutStatus.COMPLETED

    def test_process_payout_large_amount(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with large amount."""
        sample_creator["total_earnings"] = Decimal("100000.00")
        payout_amount = Decimal("50000.00")

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert result["status"] == PayoutStatus.COMPLETED
        assert result["amount"] == payout_amount

    def test_process_payout_returns_dict(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test that process_payout returns a dictionary."""
        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=Decimal("100.00"),
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert isinstance(result, dict)
        assert "status" in result
        assert "creator_id" in result
        assert "amount" in result
        assert "transaction_id" in result
        assert "processed_at" in result

    def test_process_payout_with_custom_reference(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with custom reference."""
        payout_amount = Decimal("100.00")
        reference = "PAYOUT-2024-001"

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
                reference=reference,
            )

        assert result["reference"] == reference

    def test_process_payout_multiple_content_items(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing for multiple content items."""
        sample_creator["total_earnings"] = Decimal("1000.00")
        payout_amount = Decimal("500.00")

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
                content_ids=[uuid4(), uuid4(), uuid4()],
            )

        assert result["status"] == PayoutStatus.COMPLETED
        assert "content_ids" in result
        assert len(result["content_ids"]) == 3

    def test_process_payout_idempotency_key(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with idempotency key."""
        payout_amount = Decimal("100.00")
        idempotency_key = "unique-key-123"

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            result = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
                idempotency_key=idempotency_key,
            )

        assert result["idempotency_key"] == idempotency_key

    def test_process_payout_duplicate_idempotency_key(
        self,
        creator_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
    ):
        """Test payout processing with duplicate idempotency key."""
        payout_amount = Decimal("100.00")
        idempotency_key = "duplicate-key"

        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            # First call succeeds
            result1 = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
                idempotency_key=idempotency_key,
            )

            # Second call with same key returns existing result
            result2 = process_payout(
                creator_id=creator_id,
                amount=payout_amount,
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
                idempotency_key=idempotency_key,
            )

        assert result1["transaction_id"] == result2["transaction_id"]


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------


class TestMonetizationIntegration:
    """Integration tests combining multiple monetization functions."""

    def test_full_payout_workflow(
        self,
        creator_id,
        content_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
        all_tier_configs,
    ):
        """Test complete workflow from revenue to payout."""
        # Step 1: Calculate payout
        revenue = Decimal("1000.00")
        tier_info = get_monetization_tier(
            total_earnings=Decimal("500.00"),
            tier_configs=all_tier_configs,
        )

        payout_result = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=tier_info["revenue_share"],
        )

        assert payout_result["payout_amount"] == Decimal("500.00")

        # Step 2: Process payout
        with patch(
            "ugc_marketplace.agents.creator_monetization.get_creator",
            return_value=sample_creator,
        ):
            process_result = process_payout(
                creator_id=creator_id,
                amount=payout_result["payout_amount"],
                db=mock_db,
                payout_gateway=mock_payout_gateway,
                notification_service=mock_notification_service,
            )

        assert process_result["status"] == PayoutStatus.COMPLETED
        assert process_result["amount"] == Decimal("500.00")

    def test_tier_upgrade_affects_payout(
        self,
        creator_id,
        content_id,
        sample_creator,
        mock_db,
        mock_payout_gateway,
        mock_notification_service,
        all_tier_configs,
    ):
        """Test that tier upgrade results in higher payout."""
        revenue = Decimal("1000.00")

        # Bronze tier payout
        bronze_tier = get_monetization_tier(
            total_earnings=Decimal("500.00"),
            tier_configs=all_tier_configs,
        )
        bronze_payout = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=bronze_tier["revenue_share"],
        )

        # Gold tier payout
        gold_tier = get_monetization_tier(
            total_earnings=Decimal("10000.00"),
            tier_configs=all_tier_configs,
        )
        gold_payout = calculate_payout(
            creator_id=creator_id,
            content_id=content_id,
            revenue=revenue,
            revenue_share=gold_tier["revenue_share"],
        )

        assert gold_payout["payout_amount"] > bronze_payout["payout_amount"]
        assert gold_payout["payout_amount"] == Decimal("700.00")
        assert bronze_payout["payout_amount"] == Decimal("500.00")
