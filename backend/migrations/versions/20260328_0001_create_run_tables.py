"""create evaluation run tables

Revision ID: 20260328_0001
Revises:
Create Date: 2026-03-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260328_0001"
down_revision = None
branch_labels = None
depends_on = None


run_status = sa.Enum("queued", "running", "completed", "failed", name="run_status")


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False, server_default="20"),
        sa.Column(
            "api_key_provided", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("requested_external_mcp_url", sa.Text(), nullable=True),
        sa.Column(
            "external_mcp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "sandbox_profile",
            sa.String(length=128),
            nullable=False,
            server_default="nix-sandbox-v1",
        ),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("evaluation_summary", sa.Text(), nullable=True),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_run_events_run_id", "run_events", ["run_id"], unique=False)
    op.create_index(
        "ix_run_events_created_at", "run_events", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_run_events_created_at", table_name="run_events")
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_table("evaluation_runs")
    run_status.drop(op.get_bind(), checkfirst=True)
