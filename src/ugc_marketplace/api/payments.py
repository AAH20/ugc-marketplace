"""Payment API endpoints for UGC Marketplace."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class PaymentCreate(BaseModel):
    """Schema for creating a new payment."""

    order_id: UUID = Field(..., description="Associated order ID")
    amount: float = Field(..., gt=0, description="Payment amount in currency units")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    method: str = Field(..., description="Payment method (e.g., credit_card, paypal, bank_transfer)")
    payer_id: UUID = Field(..., description="ID of the user making the payment")
    payee_id: UUID = Field(..., description="ID of the user receiving the payment")
    description: Optional[str] = Field(default=None, max_length=500, description="Optional payment description")

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class PaymentUpdate(BaseModel):
    """Schema for updating a payment's status."""

    status: str = Field(..., description="New payment status")
    transaction_id: Optional[str] = Field(default=None, description="External transaction reference")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional payment metadata")

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        allowed = {"pending", "processing", "completed", "failed", "refunded", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
        return v


class PaymentResponse(BaseModel):
    """Schema for payment response."""

    id: UUID
    order_id: UUID
    amount: float
    currency: str
    method: str
    status: str
    payer_id: UUID
    payee_id: UUID
    description: Optional[str] = None
    transaction_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    """Schema for paginated payment list response."""

    items: List[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str


# ---------------------------------------------------------------------------
# In-memory store (replace with database in production)
# ---------------------------------------------------------------------------

_payments_store: Dict[UUID, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaymentListResponse,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
    summary="List payments",
    description="Retrieve a paginated list of all payments.",
)
async def list_payments(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by payment status"),
) -> PaymentListResponse:
    """List payments with optional filtering and pagination."""
    try:
        all_payments: List[Dict[str, Any]] = list(_payments_store.values())

        if status:
            all_payments = [p for p in all_payments if p["status"] == status]

        total = len(all_payments)
        pages = (total + page_size - 1) // page_size if total > 0 else 1
        start = (page - 1) * page_size
        end = start + page_size
        paginated = all_payments[start:end]

        return PaymentListResponse(
            items=[PaymentResponse(**p) for p in paginated],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(exc)}",
        )


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=http_status.HTTP_201_CREATED,
    responses={
        201: {"description": "Payment created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Create payment",
    description="Create a new payment record.",
)
async def create_payment(payment: PaymentCreate) -> PaymentResponse:
    """Create a new payment."""
    try:
        payment_id = uuid4()
        now = "2026-10-03T00:00:00Z"  # Replace with datetime.utcnow().isoformat()

        payment_data: Dict[str, Any] = {
            "id": payment_id,
            "order_id": payment.order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "method": payment.method,
            "status": "pending",
            "payer_id": payment.payer_id,
            "payee_id": payment.payee_id,
            "description": payment.description,
            "transaction_id": None,
            "metadata": None,
            "created_at": now,
            "updated_at": now,
        }

        _payments_store[payment_id] = payment_data
        return PaymentResponse(**payment_data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(exc)}",
        )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Payment not found"},
        422: {"model": ErrorResponse, "description": "Invalid payment ID format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get payment by ID",
    description="Retrieve a single payment by its unique identifier.",
)
async def get_payment(payment_id: UUID) -> PaymentResponse:
    """Get a payment by ID."""
    try:
        payment_data = _payments_store.get(payment_id)
        if payment_data is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found",
            )
        return PaymentResponse(**payment_data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment: {str(exc)}",
        )


@router.put(
    "/{payment_id}",
    response_model=PaymentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Payment not found"},
        400: {"model": ErrorResponse, "description": "Invalid update data"},
        422: {"model": ErrorResponse, "description": "Invalid payment ID format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Update payment status",
    description="Update the status and optional fields of an existing payment.",
)
async def update_payment(payment_id: UUID, update: PaymentUpdate) -> PaymentResponse:
    """Update a payment's status."""
    try:
        payment_data = _payments_store.get(payment_id)
        if payment_data is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found",
            )

        payment_data["status"] = update.status
        if update.transaction_id is not None:
            payment_data["transaction_id"] = update.transaction_id
        if update.metadata is not None:
            payment_data["metadata"] = update.metadata
        payment_data["updated_at"] = "2026-10-03T00:00:00Z"  # Replace with datetime.utcnow().isoformat()

        return PaymentResponse(**payment_data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment: {str(exc)}",
        )


@router.delete(
    "/{payment_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Payment not found"},
        422: {"model": ErrorResponse, "description": "Invalid payment ID format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete payment",
    description="Permanently delete a payment record.",
)
async def delete_payment(payment_id: UUID) -> None:
    """Delete a payment by ID."""
    try:
        if payment_id not in _payments_store:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found",
            )
        del _payments_store[payment_id]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete payment: {str(exc)}",
        )
