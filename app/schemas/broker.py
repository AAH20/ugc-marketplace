"""Pydantic schemas for Broker API."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class BrokerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: str | None = Field(None, max_length=255)
    country: str = Field(..., min_length=2, max_length=2)
    currency: str = Field(..., min_length=3, max_length=3)
    commission_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    is_active: bool = True


class BrokerCreate(BrokerBase):
    pass


class BrokerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    name_ar: str | None = Field(None, max_length=255)
    country: str | None = Field(None, min_length=2, max_length=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
    commission_rate: Decimal | None = Field(None, ge=0, le=1, decimal_places=4)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    is_active: bool | None = None


class BrokerResponse(BrokerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
