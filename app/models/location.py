from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=True, unique=True, index=True)
    description = Column(String, nullable=False, unique=True)

    cities = relationship(
        "City", back_populates="state", cascade="all, delete-orphan"
    )

    @property
    def name(self):
        """Alias para compatibilidad con código legado."""
        return self.description


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=True, index=True)
    description = Column(String, nullable=False)
    state_id = Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), nullable=False)

    state = relationship("State", back_populates="cities")
    persons = relationship("Person", back_populates="city")
    tenants = relationship("Tenant", foreign_keys="Tenant.city_id", back_populates="city_rel")

    @property
    def name(self):
        """Alias para compatibilidad con código legado."""
        return self.description

