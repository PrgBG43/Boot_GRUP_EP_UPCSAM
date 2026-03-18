from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    chat_id = Column(String, nullable=False, index=True)
    last_interaction_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    visit_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="conversations")
