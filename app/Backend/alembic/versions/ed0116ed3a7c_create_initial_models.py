"""create_initial_models

Revision ID: ed0116ed3a7c
Revises:
Create Date: 2026-09-18 15:18:41.374203

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed0116ed3a7c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create Enum Types
    user_role_enum = postgresql.ENUM(
        "SUPPORT_AGENT",
        "SUPPORT_MANAGER",
        "SECURITY_ANALYST",
        "ADMIN",
        name="user_role",
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    conversation_channel_enum = postgresql.ENUM(
        "EMAIL",
        "CHAT",
        "TICKET",
        "SOCIAL_MEDIA",
        "OTHER",
        name="conversation_channel",
    )
    conversation_channel_enum.create(op.get_bind(), checkfirst=True)

    conversation_status_enum = postgresql.ENUM(
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED",
        name="conversation_status",
    )
    conversation_status_enum.create(op.get_bind(), checkfirst=True)

    sender_type_enum = postgresql.ENUM(
        "CUSTOMER",
        "AGENT",
        "SYSTEM",
        name="sender_type",
    )
    sender_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "SUPPORT_AGENT",
                "SUPPORT_MANAGER",
                "SECURITY_ANALYST",
                "ADMIN",
                name="user_role",
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 3. Create Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_reference", sa.String(length=64), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column(
            "channel",
            sa.Enum(
                "EMAIL",
                "CHAT",
                "TICKET",
                "SOCIAL_MEDIA",
                "OTHER",
                name="conversation_channel",
            ),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "IN_PROGRESS",
                "RESOLVED",
                "CLOSED",
                name="conversation_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "assigned_agent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversations_conversation_reference"),
        "conversations",
        ["conversation_reference"],
        unique=True,
    )
    op.create_index(
        op.f("ix_conversations_customer_email"),
        "conversations",
        ["customer_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_assigned_agent_id"),
        "conversations",
        ["assigned_agent_id"],
        unique=False,
    )

    # 4. Create Messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "sender_type",
            sa.Enum(
                "CUSTOMER",
                "AGENT",
                "SYSTEM",
                name="sender_type",
            ),
            nullable=False,
        ),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )

    # 5. Create Analyses table
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("issue", sa.String(length=255), nullable=True),
        sa.Column("sentiment", sa.String(length=50), nullable=True),
        sa.Column("emotion", sa.String(length=50), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("resolution_status", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analyses_conversation_id"),
        "analyses",
        ["conversation_id"],
        unique=False,
    )

    # 6. Create Threats table
    op.create_table(
        "threats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("threat_detected", sa.Boolean(), nullable=False, default=False),
        sa.Column("threat_type", sa.String(length=100), nullable=True),
        sa.Column(
            "social_engineering_detected",
            sa.Boolean(),
            nullable=False,
            default=False,
        ),
        sa.Column(
            "techniques",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column(
            "suspicious_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "suspicious_emails",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "risk_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_threats_conversation_id"),
        "threats",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_threats_conversation_id"), table_name="threats")
    op.drop_table("threats")

    op.drop_index(op.f("ix_analyses_conversation_id"), table_name="analyses")
    op.drop_table("analyses")

    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(
        op.f("ix_conversations_assigned_agent_id"), table_name="conversations"
    )
    op.drop_index(op.f("ix_conversations_customer_email"), table_name="conversations")
    op.drop_index(
        op.f("ix_conversations_conversation_reference"),
        table_name="conversations",
    )
    op.drop_table("conversations")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    # Drop enum types
    sa.Enum(name="sender_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conversation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conversation_channel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
