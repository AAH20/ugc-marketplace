"""Broker model with MENA-specific fields."""
import re
from sqlalchemy import String, Numeric, Boolean, CheckConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, validates, relationship
from app.models.base import Base, TimestampMixin

# MENA country codes
MENA_COUNTRIES = {
    "AE",  # UAE
    "SA",  # Saudi Arabia
    "EG",  # Egypt
    "QA",  # Qatar
    "KW",  # Kuwait
    "BH",  # Bahrain
    "OM",  # Oman
    "JO",  # Jordan
    "LB",  # Lebanon
    "IQ",  # Iraq
    "MA",  # Morocco
    "TN",  # Tunisia
    "DZ",  # Algeria
}

# Supported MENA currencies
MENA_CURRENCIES = {"AED", "SAR", "EGP", "QAR", "KWD", "BHD", "OMR", "JOD", "LBP", "IQD", "MAD", "TND", "DZD"}


class Broker(Base, TimestampMixin):
    """Broker entity for MENA market."""
    __tablename__ = "brokers"
    __table_args__ = (
        CheckConstraint("commission_rate >= 0 AND commission_rate <= 1", name="ck_commission_rate_bounds"),
        CheckConstraint(
            f"country IN ({','.join(repr(c) for c in MENA_COUNTRIES)})",
            name="ck_country_mena",
        ),
        CheckConstraint(
            f"currency IN ({','.join(repr(c) for c in MENA_CURRENCIES)})",
            name="ck_currency_mena",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.05)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    partners: Mapped[list["BrokerPartner"]] = relationship("BrokerPartner", back_populates="broker", cascade="all, delete-orphan")
    commissions: Mapped[list["CommissionTracking"]] = relationship("CommissionTracking", back_populates="broker", cascade="all, delete-orphan")
    payouts: Mapped[list["BrokerPayout"]] = relationship("BrokerPayout", back_populates="broker", cascade="all, delete-orphan")

    @validates("name_ar")
    def validate_arabic_name(self, key, value):
        """Validate that Arabic name contains Arabic characters."""
        if value is None:
            return value
        # Check for Arabic Unicode range
        if not re.search(r'[\u0600-\u06FF]', value):
            raise ValueError("Arabic name must contain Arabic characters")
        return value

    def __repr__(self):
        return f"<Broker(id={self.id}, name='{self.name}', country='{self.country}')>"
