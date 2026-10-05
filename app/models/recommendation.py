"""Recommendation model for performance optimization."""
from enum import Enum

from sqlalchemy import String, Numeric, ForeignKey, Integer, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecommendationCategory(str, Enum):
    BUDGET_REALLOCATION = "budget_reallocation"
    CTR_OPTIMIZATION = "ctr_optimization"
    SPEND_ADJUSTMENT = "spend_adjustment"
    AUDIENCE_TARGETING = "audience_targeting"
    CREATIVE_REFRESH = "creative_refresh"
    BID_OPTIMIZATION = "bid_optimization"


class Recommendation(Base):
    """Performance optimization recommendation."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[RecommendationCategory] = mapped_column(
        SAEnum(RecommendationCategory, name="recommendation_category"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Recommendation(id={self.id}, category='{self.category}', priority={self.priority})>"
