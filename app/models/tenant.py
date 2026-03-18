from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    booking_url = Column(String, nullable=True, index=True)
    owner_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    owner_user = relationship("User", back_populates="tenant_owned")
    channels = relationship(
        "Channel", back_populates="tenant", cascade="all, delete-orphan"
    )
    services = relationship(
        "Service", back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )
