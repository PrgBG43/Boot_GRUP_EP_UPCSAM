from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String, nullable=False)
    bot_token = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="channels")
