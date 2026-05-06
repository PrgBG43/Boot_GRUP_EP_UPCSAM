from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)          # free | premium | enterprise
    display_name = Column(String, nullable=False)
    max_appointments_monthly = Column(Integer, nullable=True)   # None = ilimitado
    max_active_services = Column(Integer, nullable=True)        # None = ilimitado
    max_staff = Column(Integer, nullable=True)
    allows_advanced_reminders = Column(Boolean, default=False)
    allows_analytics = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
