from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


SUPPORT_TICKET_STATUSES = ("open", "in_progress", "waiting_user", "resolved", "closed")
SUPPORT_TICKET_PRIORITIES = ("low", "normal", "high", "urgent")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="normal", index=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        index=True,
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="support_tickets")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    messages = relationship(
        "SupportTicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportTicketMessage.created_at",
    )

    @property
    def tenant_name(self):
        return self.tenant.name if self.tenant else None

    @property
    def tenant_plan(self):
        return self.tenant.plan.name if self.tenant and self.tenant.plan else None

    @property
    def tenant_plan_label(self):
        return self.tenant.plan.display_name if self.tenant and self.tenant.plan else None

    @property
    def is_premium(self):
        return self.tenant_plan == "premium"


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    is_internal_note = Column(Boolean, default=False)

    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User")

    @property
    def sender_role(self):
        return self.sender.primary_role if self.sender else None

    @property
    def sender_name(self):
        if not self.sender:
            return None
        full_name = f"{self.sender.first_name or ''} {self.sender.last_name or ''}".strip()
        return full_name or self.sender.email
