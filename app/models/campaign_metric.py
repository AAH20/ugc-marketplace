"""CampaignMetric model for time-series metrics."""
from datetime import datetime, timezone

from sqlalchemy import Integer, Numeric, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CampaignMetric(Base):
    """Time-series metrics for a campaign (hourly granularity)."""
    __tablename__ = "campaign_metrics"
    __table_args__ = (
        Index("ix_campaign_metrics_campaign_id_timestamp", "campaign_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spend: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="metrics")

    def __repr__(self):
        return f"<CampaignMetric(id={self.id}, campaign_id={self.campaign_id}, ts='{self.timestamp}')>"
