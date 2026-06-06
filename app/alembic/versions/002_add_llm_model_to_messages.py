"""add llm_model to messages

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("llm_model", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "llm_model")
