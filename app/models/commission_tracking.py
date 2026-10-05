"""CommissionTracking model."""

from datetime import date
from sqlalchemy import String, Numeric, ForeignKey, Date, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import Base, TimestampMixin


class CommissionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class CommissionTracking(Base, TimestampMixin):
    """Track commissions earned by brokers."""

    __tablename__ = "commission_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    broker_id: Mapped[int] = mapped_column(
        ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False
    )
    deal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    deal_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deal_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    deal_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[CommissionStatus] = mapped_column(
        SAEnum(CommissionStatus, name="commission_status"),
        nullable=False,
        default=CommissionStatus.PENDING,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    broker: Mapped["Broker"] = relationship("Broker", back_populates="commissions")

    def __repr__(self):
        return f"<CommissionTracking(id={self.id}, broker_id={self.broker_id}, amount={self.commission_amount})>"
