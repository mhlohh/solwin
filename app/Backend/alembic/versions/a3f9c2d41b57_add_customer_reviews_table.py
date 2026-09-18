"""add customer_reviews table

Revision ID: a3f9c2d41b57
Revises: ed0116ed3a7c
Create Date: 2026-09-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f9c2d41b57"
down_revision: Union[str, Sequence[str], None] = "ed0116ed3a7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create customer_reviews table for canonical review intelligence."""
    op.create_table(
        "customer_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("fine_grained_intent", sa.String(length=128), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("sentiment_label", sa.String(length=32), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column(
            "keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("cluster_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_name", sa.String(length=255), nullable=False),
        sa.Column("cluster_similarity_score", sa.Float(), nullable=False),
        sa.Column("urgency_level", sa.String(length=32), nullable=False),
        sa.Column("urgency_score", sa.Float(), nullable=False),
        sa.Column(
            "urgency_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("resolution_status", sa.String(length=32), nullable=False),
        sa.Column("resolution_confidence", sa.Float(), nullable=False),
        sa.Column(
            "resolution_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("security_risk_level", sa.String(length=32), nullable=False),
        sa.Column("security_risk_score", sa.Float(), nullable=False),
        sa.Column(
            "phishing", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "email_addresses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "social_engineering",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "security_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("overall_risk_level", sa.String(length=32), nullable=False),
        sa.Column("overall_risk_score", sa.Float(), nullable=False),
        sa.Column(
            "overall_risk_factors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("primary_action", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column(
            "secondary_actions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("recommendation_rationale", sa.Text(), nullable=False),
        sa.Column(
            "model_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("processing_time_ms", sa.Float(), nullable=False),
        sa.Column(
            "warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_reviews_review_id"),
        "customer_reviews",
        ["review_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_customer_reviews_category"),
        "customer_reviews",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_customer_reviews_category_urgency",
        "customer_reviews",
        ["category", "urgency_level"],
        unique=False,
    )
    op.create_index(
        "ix_customer_reviews_security_risk",
        "customer_reviews",
        ["security_risk_level"],
        unique=False,
    )


def downgrade() -> None:
    """Drop customer_reviews table."""
    op.drop_index(
        "ix_customer_reviews_security_risk", table_name="customer_reviews"
    )
    op.drop_index(
        "ix_customer_reviews_category_urgency", table_name="customer_reviews"
    )
    op.drop_index(op.f("ix_customer_reviews_category"), table_name="customer_reviews")
    op.drop_index(op.f("ix_customer_reviews_review_id"), table_name="customer_reviews")
    op.drop_table("customer_reviews")
