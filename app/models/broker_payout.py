"""BrokerPayout model."""

from datetime import date
from sqlalchemy import String, Numeric, ForeignKey, Date, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, TimestampMixin


class PayoutStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    WIRE = "wire"
    CHECK = "check"
    DIGITAL_WALLET = "digital_wallet"


class BrokerPayout(Base, TimestampMixin):
    """Track payouts to brokers."""

    __tablename__ = "broker_payouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    broker_id: Mapped[int] = mapped_column(
        ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payout_method: Mapped[PayoutMethod] = mapped_column(
        SAEnum(PayoutMethod, name="payout_method"), nullable=False
    )
    status: Mapped[PayoutStatus] = mapped_column(
        SAEnum(PayoutStatus, name="payout_status"), nullable=False, default=PayoutStatus.SCHEDULED
    )
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    broker: Mapped["Broker"] = relationship("Broker", back_populates="payouts")

    def __repr__(self):
        return f"<BrokerPayout(id={self.id}, broker_id={self.broker_id}, amount={self.amount}, status='{self.status}')>"
