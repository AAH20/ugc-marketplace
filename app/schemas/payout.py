"""Pydantic schemas for Payout API."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class PayoutCreate(BaseModel):
    broker_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    payout_method: str = Field(..., pattern="^(bank_transfer|wire|check|digital_wallet)$")
    reference_number: str | None = Field(None, max_length=100)
    bank_name: str | None = Field(None, max_length=255)
    bank_account_last4: str | None = Field(None, max_length=4)
    iban: str | None = Field(None, max_length=34)
    scheduled_date: date | None = None
    notes: str | None = None


class PayoutUpdate(BaseModel):
    status: str = Field(..., pattern="^(scheduled|processing|completed|failed|cancelled)$")
    completed_date: date | None = None


class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_id: int
    amount: Decimal
    currency: str
    payout_method: str
    status: str
    reference_number: str | None
    bank_name: str | None
    bank_account_last4: str | None
    iban: str | None
    scheduled_date: date | None
    completed_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PayoutSummaryResponse(BaseModel):
    broker_id: int
    total_amount: Decimal
    currency: str
    count: int
