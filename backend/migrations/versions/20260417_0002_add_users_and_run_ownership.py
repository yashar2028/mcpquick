"""add users and run ownership

Revision ID: 20260417_0002
Revises: 20260328_0001
Create Date: 2026-04-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_0002"
down_revision = "20260328_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, password_hash, full_name)
            VALUES ('00000000-0000-0000-0000-000000000001',
                    'legacy@mcpquick.local',
                    'legacy-account-no-login',
                    'Legacy Runs')
            """
        )
    )

    op.add_column(
        "evaluation_runs",
        sa.Column("user_id", sa.String(length=36), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE evaluation_runs "
            "SET user_id = '00000000-0000-0000-0000-000000000001' "
            "WHERE user_id IS NULL"
        )
    )

    op.alter_column("evaluation_runs", "user_id", nullable=False)
    op.create_index(
        "ix_evaluation_runs_user_id", "evaluation_runs", ["user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_evaluation_runs_user_id_users",
        "evaluation_runs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_evaluation_runs_user_id_users", "evaluation_runs", type_="foreignkey"
    )
    op.drop_index("ix_evaluation_runs_user_id", table_name="evaluation_runs")
    op.drop_column("evaluation_runs", "user_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
