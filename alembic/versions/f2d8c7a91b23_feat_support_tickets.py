"""feat support tickets

Revision ID: f2d8c7a91b23
Revises: c55d95de37f2
Create Date: 2026-05-23 08:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2d8c7a91b23"
down_revision: Union[str, None] = "c55d95de37f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("support_tickets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_support_tickets_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_tickets_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_tickets_priority"), ["priority"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_tickets_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_tickets_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_tickets_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_internal_note", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("support_ticket_messages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_support_ticket_messages_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_ticket_messages_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_support_ticket_messages_ticket_id"), ["ticket_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("support_ticket_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_support_ticket_messages_ticket_id"))
        batch_op.drop_index(batch_op.f("ix_support_ticket_messages_id"))
        batch_op.drop_index(batch_op.f("ix_support_ticket_messages_created_at"))
    op.drop_table("support_ticket_messages")

    with op.batch_alter_table("support_tickets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_support_tickets_updated_at"))
        batch_op.drop_index(batch_op.f("ix_support_tickets_tenant_id"))
        batch_op.drop_index(batch_op.f("ix_support_tickets_status"))
        batch_op.drop_index(batch_op.f("ix_support_tickets_priority"))
        batch_op.drop_index(batch_op.f("ix_support_tickets_id"))
        batch_op.drop_index(batch_op.f("ix_support_tickets_created_at"))
    op.drop_table("support_tickets")
