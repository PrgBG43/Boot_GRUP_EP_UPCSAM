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
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    chat_id = Column(String, nullable=False, index=True)
    bot_id = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=False, default="telegram")
    status = Column(String, nullable=False, default="active")
    current_step = Column(String, nullable=True)
    context_data = Column(String, nullable=True)
    last_interaction_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    visit_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="conversations")
    client = relationship("Client", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    @property
    def tenant_name(self):
        return self.tenant.name if self.tenant else None

    @property
    def client_name(self):
        return self.client.full_name if self.client else None
