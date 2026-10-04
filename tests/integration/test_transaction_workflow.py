"""Integration tests for transaction workflows.

Tests the full lifecycle of transactions including creation, status updates,
deletion, payment processing, and fraud detection.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Load the fraud_detection module directly since the package shadows it
_module_path = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "ugc_marketplace"
    / "agents"
    / "_fraud_detection.py"
)
_spec = importlib.util.spec_from_file_location("_fraud_detection_module", _module_path)
_fraud_detection = importlib.util.module_from_spec(_spec)
sys.modules["_fraud_detection_module"] = _fraud_detection
_spec.loader.exec_module(_fraud_detection)

detect_fraud = _fraud_detection.detect_fraud
flag_suspicious_activity = _fraud_detection.flag_suspicious_activity
get_fraud_score = _fraud_detection.get_fraud_score
investigate_fraud = _fraud_detection.investigate_fraud
FraudRiskLevel = _fraud_detection.FraudRiskLevel

from ugc_marketplace.services.payment_service import (
    create_payment,
    get_payment,
    update_payment_status,
)
from ugc_marketplace.services.transaction_service import (
    RefundReason,
    TransactionNotFoundError,
    TransactionStatus,
    cancel_transaction,
    complete_transaction,
    create_transaction,
    delete_transaction,
    get_transaction,
    process_refund,
    update_transaction_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_transaction_data() -> dict:
    """Provide sample data for creating a transaction."""
    return {
        "buyer_id": "user-buyer-001",
        "seller_id": "user-seller-001",
        "amount": 49.99,
        "currency": "USD",
        "description": "Test transaction",
    }


@pytest.fixture
def sample_payment_data() -> dict:
    """Provide sample data for creating a payment."""
    return {
        "user_id": "user-buyer-001",
        "amount": 49.99,
        "currency": "USD",
        "payment_method": "credit_card",
        "description": "Test payment",
    }


@pytest.fixture
def created_transaction(sample_transaction_data: dict) -> dict:
    """Create a transaction and return its data."""
    return create_transaction(sample_transaction_data)


@pytest.fixture
def created_payment(sample_payment_data: dict) -> dict:
    """Create a payment and return its data."""
    return create_payment(sample_payment_data)


# ---------------------------------------------------------------------------
# Test: Full Transaction Lifecycle
# ---------------------------------------------------------------------------


class TestFullTransactionLifecycle:
    """Tests for the complete transaction lifecycle: create -> update -> delete."""

    def test_full_transaction_lifecycle(self, sample_transaction_data: dict) -> None:
        """Test creating a transaction, updating its status, and deleting it."""
        # Create
        txn = create_transaction(sample_transaction_data)
        assert txn is not None
        assert txn["status"] == "pending"
        assert txn["buyer_id"] == sample_transaction_data["buyer_id"]
        assert txn["seller_id"] == sample_transaction_data["seller_id"]
        assert txn["amount"] == sample_transaction_data["amount"]
        assert txn["currency"] == sample_transaction_data["currency"]
        txn_id = txn["id"]

        # Verify it exists
        fetched = get_transaction(txn_id)
        assert fetched is not None
        assert fetched["id"] == txn_id
        assert fetched["status"] == "pending"

        # Update status to completed
        updated = update_transaction_status(txn_id, "completed")
        assert updated is not None
        assert updated["status"] == "completed"
        assert updated["id"] == txn_id

        # Verify the update persisted
        fetched = get_transaction(txn_id)
        assert fetched is not None
        assert fetched["status"] == "completed"

        # Delete
        result = delete_transaction(txn_id)
        assert result is True

        # Verify it's gone
        with pytest.raises(TransactionNotFoundError):
            get_transaction(txn_id)

    def test_transaction_lifecycle_with_cancellation(self, sample_transaction_data: dict) -> None:
        """Test creating and cancelling a transaction."""
        txn = create_transaction(sample_transaction_data)
        txn_id = txn["id"]

        # Cancel the transaction
        cancelled = cancel_transaction(txn_id)
        assert cancelled.status == TransactionStatus.FAILED

        # Verify the status changed
        fetched = get_transaction(txn_id)
        assert fetched["status"] == "failed"

    def test_transaction_lifecycle_with_completion(self, sample_transaction_data: dict) -> None:
        """Test creating and completing a transaction."""
        txn = create_transaction(sample_transaction_data)
        txn_id = txn["id"]

        # Complete the transaction
        completed = complete_transaction(txn_id)
        assert completed.status == TransactionStatus.COMPLETED

        # Verify the status changed
        fetched = get_transaction(txn_id)
        assert fetched["status"] == "completed"


# ---------------------------------------------------------------------------
# Test: Transaction Payment Flow
# ---------------------------------------------------------------------------


class TestTransactionPaymentFlow:
    """Tests for the transaction and payment integration flow."""

    def test_transaction_payment_flow(
        self, sample_transaction_data: dict, sample_payment_data: dict
    ) -> None:
        """Test creating a transaction, creating a payment, and updating status."""
        # Create transaction
        txn = create_transaction(sample_transaction_data)
        assert txn is not None
        assert txn["status"] == "pending"
        txn_id = txn["id"]

        # Create payment for the transaction
        payment_data = {**sample_payment_data, "user_id": txn["buyer_id"]}
        payment = create_payment(payment_data)
        assert payment is not None
        assert payment["status"] == "pending"
        assert payment["user_id"] == txn["buyer_id"]
        assert payment["amount"] == txn["amount"]
        payment_id = payment["payment_id"]

        # Verify payment exists
        fetched_payment = get_payment(payment_id)
        assert fetched_payment is not None
        assert fetched_payment["payment_id"] == payment_id

        # Update payment status to completed
        updated_payment = update_payment_status(payment_id, "completed")
        assert updated_payment is not None
        assert updated_payment["status"] == "completed"

        # Update transaction status to completed
        updated_txn = update_transaction_status(txn_id, "completed")
        assert updated_txn is not None
        assert updated_txn["status"] == "completed"

        # Verify both are updated
        fetched_txn = get_transaction(txn_id)
        assert fetched_txn["status"] == "completed"
        fetched_payment = get_payment(payment_id)
        assert fetched_payment["status"] == "completed"

    def test_transaction_payment_flow_with_refund(
        self, sample_transaction_data: dict, sample_payment_data: dict
    ) -> None:
        """Test the full payment flow including refund."""
        # Create transaction
        txn = create_transaction(sample_transaction_data)
        txn_id = txn["id"]

        # Create and complete payment
        payment_data = {**sample_payment_data, "user_id": txn["buyer_id"]}
        payment = create_payment(payment_data)
        payment_id = payment["payment_id"]
        update_payment_status(payment_id, "completed")
        update_transaction_status(txn_id, "completed")

        # Process refund
        refunded_txn = process_refund(txn_id, reason=RefundReason.BUYER_REMORSE)
        assert refunded_txn.status == TransactionStatus.REFUNDED

        # Update payment status to refunded
        updated_payment = update_payment_status(payment_id, "refunded")
        assert updated_payment["status"] == "refunded"


# ---------------------------------------------------------------------------
# Test: Transaction Fraud Detection
# ---------------------------------------------------------------------------


class TestTransactionFraudDetection:
    """Tests for fraud detection integration with transactions."""

    def test_transaction_fraud_detection(self, sample_transaction_data: dict) -> None:
        """Test creating a transaction, detecting fraud, and flagging."""
        # Create transaction
        txn = create_transaction(sample_transaction_data)
        assert txn is not None
        txn_id = txn["id"]
        user_id = txn["buyer_id"]

        # Detect fraud for the transaction
        fraud_score = detect_fraud(txn_id)
        assert fraud_score is not None
        assert fraud_score.transaction_id == txn_id
        assert 0 <= fraud_score.score <= 1
        assert fraud_score.risk_level in FraudRiskLevel

        # Investigate fraud
        investigation = investigate_fraud(txn_id)
        assert investigation is not None
        assert investigation.transaction_id == txn_id
        assert investigation.risk_level in FraudRiskLevel

        # Flag suspicious activity for the user
        is_suspicious = flag_suspicious_activity(
            user_id,
            {
                "type": "account_takeover",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert is_suspicious is True

        # Get user fraud score
        user_score = get_fraud_score(user_id)
        assert user_score is not None
        assert 0 <= user_score <= 1

    def test_transaction_fraud_detection_with_normal_activity(
        self, sample_transaction_data: dict
    ) -> None:
        """Test fraud detection with normal (non-suspicious) activity."""
        txn = create_transaction(sample_transaction_data)
        txn_id = txn["id"]
        user_id = txn["buyer_id"]

        # Detect fraud
        fraud_score = detect_fraud(txn_id)
        assert fraud_score is not None

        # Flag normal activity
        is_suspicious = flag_suspicious_activity(
            user_id,
            {
                "type": "login",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert is_suspicious is False

        # User score should be low
        user_score = get_fraud_score(user_id)
        assert user_score < 0.5

    def test_transaction_fraud_detection_with_suspicious_patterns(
        self, sample_transaction_data: dict
    ) -> None:
        """Test fraud detection with multiple suspicious activities."""
        txn = create_transaction(sample_transaction_data)
        user_id = txn["buyer_id"]

        # Flag multiple suspicious activities
        suspicious_activities = [
            {
                "type": "account_takeover",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "type": "chargeback",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "type": "fake_review",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        for activity in suspicious_activities:
            is_suspicious = flag_suspicious_activity(user_id, activity)
            assert is_suspicious is True

        # User score should be high
        user_score = get_fraud_score(user_id)
        assert user_score > 0.5
