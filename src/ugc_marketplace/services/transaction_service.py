"""Transaction service for UGC marketplace.

Handles creation, retrieval, status updates, and deletion of marketplace transactions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TransactionError(Exception):
    """Base exception for transaction-related errors."""


class TransactionNotFoundError(TransactionError):
    """Raised when a transaction cannot be found."""


class TransactionValidationError(TransactionError):
    """Raised when transaction data fails validation."""


class TransactionStateError(TransactionError):
    """Raised when an operation is invalid for the current transaction state."""


class TransactionStatus(str, Enum):
    """Possible statuses for a transaction."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class RefundReason(str, Enum):
    """Valid reasons for processing a refund."""

    BUYER_REMORSE = "buyer_remorse"
    SELLER_CANCELLED = "seller_cancelled"
    FRAUD = "fraud"
    DUPLICATE = "duplicate"
    OTHER = "other"


@dataclass
class Transaction:
    """Represents a marketplace transaction."""

    id: str
    buyer_id: str
    seller_id: str
    amount: float
    currency: str
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    refunds: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def refunded_amount(self) -> float:
        """Total amount refunded so far."""
        return sum(r["amount"] for r in self.refunds)

    @property
    def remaining_amount(self) -> float:
        """Amount still eligible for refund."""
        return self.amount - self.refunded_amount

    def to_dict(self) -> Dict[str, Any]:
        """Serialize transaction to dictionary."""
        return {
            "id": self.id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "description": self.description,
            "metadata": self.metadata,
            "refunds": self.refunds,
            "refunded_amount": self.refunded_amount,
            "remaining_amount": self.remaining_amount,
        }


# In-memory store — replace with database integration in production
_transactions: Dict[str, Transaction] = {}


def _validate_transaction_data(data: Dict[str, Any]) -> None:
    """Validate transaction creation data.

    Raises:
        TransactionValidationError: If required fields are missing or invalid.
    """
    required_fields = ["buyer_id", "seller_id", "amount", "currency"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise TransactionValidationError(
            f"Missing required fields: {', '.join(missing)}"
        )

    if not isinstance(data["buyer_id"], str) or not data["buyer_id"].strip():
        raise TransactionValidationError("buyer_id must be a non-empty string")

    if not isinstance(data["seller_id"], str) or not data["seller_id"].strip():
        raise TransactionValidationError("seller_id must be a non-empty string")

    if data["buyer_id"] == data["seller_id"]:
        raise TransactionValidationError("buyer_id and seller_id must differ")

    if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
        raise TransactionValidationError("amount must be a positive number")

    if not isinstance(data["currency"], str) or len(data["currency"]) != 3:
        raise TransactionValidationError("currency must be a 3-letter ISO code")


def get_transaction(transaction_id: str) -> dict:
    """Get a transaction by its ID.

    Args:
        transaction_id: The unique identifier of the transaction.

    Returns:
        A dictionary containing the transaction data.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionValidationError: If transaction_id is empty or invalid.
    """
    if not transaction_id or not isinstance(transaction_id, str):
        raise TransactionValidationError("transaction_id must be a non-empty string")

    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )
    return transaction.to_dict()


def list_transactions(
    filters: dict, page: int, page_size: int
) -> list[dict]:
    """List transactions with optional filters and pagination.

    Args:
        filters: A dictionary of filter criteria. Supported keys:
            - buyer_id (str): Filter by buyer.
            - seller_id (str): Filter by seller.
            - status (str): Filter by status.
        page: The page number (1-indexed).
        page_size: The number of transactions per page.

    Returns:
        A list of transaction dictionaries matching the filters.

    Raises:
        TransactionValidationError: If page or page_size is invalid.
    """
    if page < 1:
        raise TransactionValidationError("page must be >= 1")
    if page_size < 1:
        raise TransactionValidationError("page_size must be >= 1")

    results = list(_transactions.values())

    buyer_id = filters.get("buyer_id")
    if buyer_id is not None:
        results = [t for t in results if t.buyer_id == buyer_id]

    seller_id = filters.get("seller_id")
    if seller_id is not None:
        results = [t for t in results if t.seller_id == seller_id]

    status = filters.get("status")
    if status is not None:
        results = [t for t in results if t.status.value == status]

    offset = (page - 1) * page_size
    paginated = results[offset : offset + page_size]

    return [t.to_dict() for t in paginated]


def create_transaction(data: dict) -> dict:
    """Create a new transaction.

    Args:
        data: A dictionary containing the transaction data:
            - buyer_id (str): ID of the buyer.
            - seller_id (str): ID of the seller.
            - amount (float): Transaction amount.
            - currency (str): 3-letter ISO currency code.
            - description (str, optional): Transaction description.
            - metadata (dict, optional): Additional metadata.

    Returns:
        A dictionary containing the created transaction data.

    Raises:
        TransactionValidationError: If data fails validation.
    """
    _validate_transaction_data(data)

    now = datetime.now(timezone.utc)
    transaction = Transaction(
        id=str(uuid.uuid4()),
        buyer_id=data["buyer_id"],
        seller_id=data["seller_id"],
        amount=float(data["amount"]),
        currency=data["currency"].upper(),
        status=TransactionStatus.PENDING,
        created_at=now,
        updated_at=now,
        description=data.get("description"),
        metadata=data.get("metadata", {}),
    )

    _transactions[transaction.id] = transaction
    return transaction.to_dict()


def update_transaction_status(transaction_id: str, status: str) -> dict:
    """Update the status of a transaction.

    Args:
        transaction_id: The unique identifier of the transaction.
        status: The new status to set. Must be a valid TransactionStatus value.

    Returns:
        A dictionary containing the updated transaction data.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionValidationError: If the status is invalid.
    """
    if not transaction_id or not isinstance(transaction_id, str):
        raise TransactionValidationError("transaction_id must be a non-empty string")

    try:
        new_status = TransactionStatus(status)
    except ValueError:
        valid = ", ".join(s.value for s in TransactionStatus)
        raise TransactionValidationError(
            f"Invalid status '{status}'. Valid statuses: {valid}"
        )

    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )

    transaction.status = new_status
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction.to_dict()


def delete_transaction(transaction_id: str) -> bool:
    """Delete a transaction by its ID.

    Args:
        transaction_id: The unique identifier of the transaction.

    Returns:
        True if the transaction was successfully deleted.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionValidationError: If transaction_id is empty or invalid.
    """
    if not transaction_id or not isinstance(transaction_id, str):
        raise TransactionValidationError("transaction_id must be a non-empty string")

    if transaction_id not in _transactions:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )

    del _transactions[transaction_id]
    return True


def process_refund(
    transaction_id: str,
    amount: Optional[float] = None,
    reason: RefundReason = RefundReason.OTHER,
) -> Transaction:
    """Process a refund for a transaction.

    If no amount is provided, refunds the full remaining eligible amount.

    Args:
        transaction_id: The transaction to refund.
        amount: Amount to refund. Defaults to full remaining amount.
        reason: Reason for the refund.

    Returns:
        The updated Transaction object.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionStateError: If the transaction cannot be refunded.
        TransactionValidationError: If the refund amount is invalid.
    """
    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )

    if transaction.status == TransactionStatus.REFUNDED:
        raise TransactionStateError(
            f"Transaction {transaction_id} has already been fully refunded"
        )

    if transaction.status == TransactionStatus.FAILED:
        raise TransactionStateError(
            f"Cannot refund failed transaction {transaction_id}"
        )

    if transaction.status == TransactionStatus.PENDING:
        raise TransactionStateError(
            f"Cannot refund pending transaction {transaction_id} — "
            "complete or cancel it first"
        )

    refund_amount = amount if amount is not None else transaction.remaining_amount

    if refund_amount <= 0:
        raise TransactionValidationError("Refund amount must be positive")

    if refund_amount > transaction.remaining_amount:
        raise TransactionValidationError(
            f"Refund amount {refund_amount} exceeds remaining "
            f"eligible amount {transaction.remaining_amount}"
        )

    now = datetime.now(timezone.utc)
    transaction.refunds.append({
        "amount": refund_amount,
        "reason": reason.value,
        "processed_at": now.isoformat(),
    })
    transaction.updated_at = now

    if transaction.refunded_amount >= transaction.amount:
        transaction.status = TransactionStatus.REFUNDED
    else:
        transaction.status = TransactionStatus.PARTIALLY_REFUNDED

    return transaction


def cancel_transaction(transaction_id: str) -> Transaction:
    """Cancel a pending transaction.

    Args:
        transaction_id: The transaction to cancel.

    Returns:
        The updated Transaction object.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionStateError: If the transaction is not in a cancellable state.
    """
    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )

    if transaction.status != TransactionStatus.PENDING:
        raise TransactionStateError(
            f"Cannot cancel transaction {transaction_id} "
            f"with status {transaction.status.value}"
        )

    transaction.status = TransactionStatus.FAILED
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction


def complete_transaction(transaction_id: str) -> Transaction:
    """Mark a pending transaction as completed.

    Args:
        transaction_id: The transaction to complete.

    Returns:
        The updated Transaction object.

    Raises:
        TransactionNotFoundError: If the transaction does not exist.
        TransactionStateError: If the transaction is not pending.
    """
    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction not found: {transaction_id}"
        )

    if transaction.status != TransactionStatus.PENDING:
        raise TransactionStateError(
            f"Cannot complete transaction {transaction_id} "
            f"with status {transaction.status.value}"
        )

    transaction.status = TransactionStatus.COMPLETED
    transaction.updated_at = datetime.now(timezone.utc)
    return transaction
