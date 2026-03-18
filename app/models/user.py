from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


role_permission_table = Table(
    "role_has_permission",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_permission_table = Table(
    "user_has_permission",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_role_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(
        Integer, ForeignKey("persons.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    person = relationship("Person", back_populates="user")
    tenant_owned = relationship("Tenant", back_populates="owner_user", uselist=False)
    roles = relationship("Role", secondary=user_role_table, back_populates="users")
    permissions = relationship(
        "Permission", secondary=user_permission_table, back_populates="users"
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    permissions = relationship(
        "Permission",
        secondary=role_permission_table,
        back_populates="roles",
    )
    users = relationship("User", secondary=user_role_table, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    roles = relationship(
        "Role",
        secondary=role_permission_table,
        back_populates="permissions",
    )
    users = relationship(
        "User",
        secondary=user_permission_table,
        back_populates="permissions",
    )
