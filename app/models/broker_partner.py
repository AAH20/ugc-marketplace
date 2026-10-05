"""BrokerPartner model."""
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class BrokerPartner(Base, TimestampMixin):
    """Partner associated with a broker."""
    __tablename__ = "broker_partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    broker_id: Mapped[int] = mapped_column(ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    broker: Mapped["Broker"] = relationship("Broker", back_populates="partners")

    def __repr__(self):
        return f"<BrokerPartner(id={self.id}, name='{self.partner_name}', broker_id={self.broker_id})>"
