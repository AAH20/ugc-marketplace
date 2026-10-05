"""Campaign model."""

from typing import TYPE_CHECKING
from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import String, Numeric, Boolean, Date, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from app.models.campaign_metric import CampaignMetric


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Campaign(Base, TimestampMixin):
    """Marketing campaign entity."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        SAEnum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    budget: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    spent: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    target_roas: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=2.0)
    target_ctr: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.01)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    metrics: Mapped[list["CampaignMetric"]] = relationship(
        "CampaignMetric", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"
