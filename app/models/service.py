from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="services")
