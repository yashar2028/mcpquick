"""add judge report

Revision ID: 20260515_0004
Revises: 20260502_0003
Create Date: 2026-05-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0004"
down_revision = "20260502_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column("judge_report", sa.JSON(), nullable=True),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("judge_model", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "judge_model")
    op.drop_column("evaluation_runs", "judge_report")
