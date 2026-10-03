"""
Transaction API endpoints for UGC Marketplace.

Provides:
  GET    /api/v1/transactions        — list with pagination and filtering
  POST   /api/v1/transactions        — create a new transaction
  GET    /api/v1/transactions/{id}   — get a single transaction by ID
  PUT    /api/v1/transactions/{id}   — update transaction status
  DELETE /api/v1/transactions/{id}   — delete a transaction
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TransactionStatus(Enum):
    """Valid transaction statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class TransactionType(Enum):
    """Valid transaction types."""

    PURCHASE = "purchase"
    SALE = "sale"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class TransactionBase(BaseModel):
    """Base transaction model with shared fields."""

    model_config = ConfigDict(from_attributes=True)

    buyer_id: UUID = Field(..., description="UUID of the buyer")
    seller_id: UUID = Field(..., description="UUID of the seller")
    amount: float = Field(..., gt=0, description="Transaction amount in currency units")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="ISO 4217 currency code"
    )
    type: TransactionType = Field(..., description="Type of transaction")
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING, description="Current transaction status"
    )
    description: str | None = Field(
        default=None, max_length=500, description="Optional transaction description"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional transaction metadata"
    )


class TransactionCreate(BaseModel):
    """Model for creating a new transaction."""

    buyer_id: UUID = Field(..., description="UUID of the buyer")
    seller_id: UUID = Field(..., description="UUID of the seller")
    amount: float = Field(..., gt=0, description="Transaction amount in currency units")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="ISO 4217 currency code"
    )
    type: TransactionType = Field(..., description="Type of transaction")
    description: str | None = Field(
        default=None, max_length=500, description="Optional transaction description"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional transaction metadata"
    )


class TransactionUpdate(BaseModel):
    """Model for updating an existing transaction."""

    status: TransactionStatus = Field(..., description="New transaction status")
    description: str | None = Field(default=None, max_length=500, description="Updated description")
    metadata: dict[str, Any] | None = Field(default=None, description="Updated metadata")


class TransactionResponse(TransactionBase):
    """Full transaction response model."""

    id: UUID = Field(..., description="Unique transaction identifier")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    items: list[TransactionResponse] = Field(..., description="List of transactions")
    total: int = Field(..., description="Total number of transactions matching the query")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Error description")
    code: str | None = Field(default=None, description="Machine-readable error code")


# ---------------------------------------------------------------------------
# In-memory store (replace with actual database in production)
# ---------------------------------------------------------------------------

_transactions: dict[UUID, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_transaction_or_404(transaction_id: UUID) -> dict[str, Any]:
    """Retrieve a transaction by ID or raise a 404 error."""
    transaction = _transactions.get(transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id '{transaction_id}' not found",
        )
    return transaction


def _paginate_items(
    items: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int, int]:
    """Paginate a list of items and return the slice along with pagination metadata."""
    total = len(items)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total, pages


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="List transactions",
    description="Retrieve a paginated list of transactions with optional filtering.",
    responses={
        200: {"description": "Successful response with paginated transactions"},
        422: {"model": ErrorResponse, "description": "Validation error in query parameters"},
    },
)
async def list_transactions(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    status_filter: TransactionStatus | None = Query(
        default=None, alias="status", description="Filter by transaction status"
    ),
    type_filter: TransactionType | None = Query(
        default=None, alias="type", description="Filter by transaction type"
    ),
    buyer_id: UUID | None = Query(default=None, description="Filter by buyer UUID"),
    seller_id: UUID | None = Query(default=None, description="Filter by seller UUID"),
) -> TransactionListResponse:
    """
    List all transactions with pagination and optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page (max 100).
        status_filter: Optional status filter.
        type_filter: Optional type filter.
        buyer_id: Optional buyer UUID filter.
        seller_id: Optional seller UUID filter.

    Returns:
        Paginated list of transactions.
    """
    # Collect all transactions
    all_transactions: list[dict[str, Any]] = list(_transactions.values())

    # Apply filters
    if status_filter is not None:
        all_transactions = [t for t in all_transactions if t["status"] == status_filter.value]
    if type_filter is not None:
        all_transactions = [t for t in all_transactions if t["type"] == type_filter.value]
    if buyer_id is not None:
        all_transactions = [t for t in all_transactions if t["buyer_id"] == str(buyer_id)]
    if seller_id is not None:
        all_transactions = [t for t in all_transactions if t["seller_id"] == str(seller_id)]

    # Sort by created_at descending (most recent first)
    all_transactions.sort(key=lambda t: t["created_at"], reverse=True)

    # Paginate
    paginated_items, total, pages = _paginate_items(all_transactions, page, page_size)

    return TransactionListResponse(
        items=[TransactionResponse(**item) for item in paginated_items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new transaction",
    description="Create a new transaction record.",
    responses={
        201: {"description": "Transaction created successfully"},
        422: {"model": ErrorResponse, "description": "Validation error in request body"},
    },
)
async def create_transaction(payload: TransactionCreate) -> TransactionResponse:
    """
    Create a new transaction.

    Args:
        payload: Transaction creation data.

    Returns:
        The newly created transaction.
    """
    now = datetime.now(UTC)
    transaction_id = uuid4()

    transaction_data: dict[str, Any] = {
        "id": str(transaction_id),
        "buyer_id": str(payload.buyer_id),
        "seller_id": str(payload.seller_id),
        "amount": payload.amount,
        "currency": payload.currency,
        "type": payload.type.value,
        "status": TransactionStatus.PENDING.value,
        "description": payload.description,
        "metadata": payload.metadata,
        "created_at": now,
        "updated_at": None,
    }

    _transactions[transaction_id] = transaction_data

    return TransactionResponse(**transaction_data)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="Retrieve a single transaction by its UUID.",
    responses={
        200: {"description": "Transaction found and returned"},
        404: {"model": ErrorResponse, "description": "Transaction not found"},
        422: {"model": ErrorResponse, "description": "Invalid UUID format"},
    },
)
async def get_transaction(transaction_id: UUID) -> TransactionResponse:
    """
    Get a transaction by its ID.

    Args:
        transaction_id: The UUID of the transaction to retrieve.

    Returns:
        The requested transaction.
    """
    transaction = _get_transaction_or_404(transaction_id)
    return TransactionResponse(**transaction)


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction status",
    description="Update the status and/or metadata of an existing transaction.",
    responses={
        200: {"description": "Transaction updated successfully"},
        404: {"model": ErrorResponse, "description": "Transaction not found"},
        422: {"model": ErrorResponse, "description": "Validation error in request body"},
    },
)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
) -> TransactionResponse:
    """
    Update an existing transaction.

    Args:
        transaction_id: The UUID of the transaction to update.
        payload: Update data (status, description, metadata).

    Returns:
        The updated transaction.
    """
    transaction = _get_transaction_or_404(transaction_id)

    # Update fields
    transaction["status"] = payload.status.value
    if payload.description is not None:
        transaction["description"] = payload.description
    if payload.metadata is not None:
        transaction["metadata"] = payload.metadata
    transaction["updated_at"] = datetime.now(UTC)

    _transactions[transaction_id] = transaction

    return TransactionResponse(**transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
    description="Permanently delete a transaction by its UUID.",
    responses={
        204: {"description": "Transaction deleted successfully"},
        404: {"model": ErrorResponse, "description": "Transaction not found"},
        422: {"model": ErrorResponse, "description": "Invalid UUID format"},
    },
)
async def delete_transaction(transaction_id: UUID) -> None:
    """
    Delete a transaction by its ID.

    Args:
        transaction_id: The UUID of the transaction to delete.

    Returns:
        None (204 No Content).
    """
    _get_transaction_or_404(transaction_id)
    del _transactions[transaction_id]
