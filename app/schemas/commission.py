"""Pydantic schemas for Commission API."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class CommissionCalculateRequest(BaseModel):
    broker_id: int
    deal_amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)


class CommissionCalculateResponse(BaseModel):
    broker_id: int
    deal_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    currency: str


class CommissionCreate(BaseModel):
    broker_id: int
    deal_id: str = Field(..., min_length=1, max_length=100)
    deal_description: str | None = None
    deal_amount: Decimal = Field(..., gt=0, decimal_places=2)
    commission_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    commission_amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    deal_date: date
    notes: str | None = None


class CommissionUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|paid|disputed|cancelled)$")


class CommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_id: int
    deal_id: str
    deal_description: str | None
    deal_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    currency: str
    deal_date: date
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
