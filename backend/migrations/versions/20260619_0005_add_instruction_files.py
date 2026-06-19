"""add instruction files

Revision ID: 20260619_0005
Revises: 20260515_0004
Create Date: 2026-06-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0005"
down_revision = "20260515_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_instruction_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=240), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("upload_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "upload_order", name="uq_run_instruction_files_order"
        ),
    )

    op.create_index(
        "ix_run_instruction_files_run_id",
        "run_instruction_files",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_run_instruction_files_run_id_upload_order",
        "run_instruction_files",
        ["run_id", "upload_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_run_instruction_files_run_id_upload_order",
        table_name="run_instruction_files",
    )
    op.drop_index("ix_run_instruction_files_run_id", table_name="run_instruction_files")
    op.drop_table("run_instruction_files")
