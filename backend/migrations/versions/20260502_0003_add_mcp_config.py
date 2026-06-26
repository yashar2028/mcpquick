"""add mcp config

Revision ID: 20260502_0003
Revises: 20260417_0002
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_0003"
down_revision = "20260417_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column("mcp_config", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "mcp_config")
