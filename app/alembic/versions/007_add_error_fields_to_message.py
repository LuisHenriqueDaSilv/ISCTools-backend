"""add error fields to message

Revision ID: 007
Revises: 006
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("is_error", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "messages",
        sa.Column("error_code", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "error_code")
    op.drop_column("messages", "is_error")
