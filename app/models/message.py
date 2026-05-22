from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base

# Direcciones válidas para un mensaje
MESSAGE_DIRECTIONS = ("incoming", "outgoing")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    direction = Column(String, nullable=False)  # "incoming" | "outgoing"
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")

