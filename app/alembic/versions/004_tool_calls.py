"""tool calls

Revision ID: 004
Revises: 003
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("tool_calls")
