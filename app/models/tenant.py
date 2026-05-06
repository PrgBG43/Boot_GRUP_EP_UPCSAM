from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    slug = Column(String, nullable=True, unique=True, index=True)
    opening_time = Column(String, nullable=True, default="08:00")
    closing_time = Column(String, nullable=True, default="20:00")
    booking_url = Column(String, nullable=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    owner_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    plan = relationship("Plan")
    owner_user = relationship("User", foreign_keys=[owner_user_id], back_populates="tenant_owned")
    users = relationship("User", foreign_keys="User.tenant_id", back_populates="tenant")
    channels = relationship(
        "Channel", back_populates="tenant", cascade="all, delete-orphan"
    )
    services = relationship(
        "Service", back_populates="tenant", cascade="all, delete-orphan"
    )
    clients = relationship(
        "Client", back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )
    appointments = relationship(
        "Appointment", back_populates="tenant", cascade="all, delete-orphan"
    )
    telegram_config = relationship(
        "TelegramConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )

