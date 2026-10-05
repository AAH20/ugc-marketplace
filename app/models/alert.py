"""Alert model for anomaly detection."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import String, Numeric, ForeignKey, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertType(str, Enum):
    SPEND_SPIKE = "spend_spike"
    CTR_DROP = "ctr_drop"
    LOW_ROAS = "low_roas"
    BUDGET_EXHAUSTION = "budget_exhaustion"
    CONVERSION_DROP = "conversion_drop"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Alert generated when an anomaly is detected."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type"), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity, name="alert_severity"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"
