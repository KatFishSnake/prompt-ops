"""add scenario jobs

Revision ID: 002
Revises: 001
Create Date: 2024-01-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenario_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("total", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "scenario_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenario_jobs.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("role", sa.String(255), server_default=""),
        sa.Column("message", sa.Text(), server_default=""),
        sa.Column("variables", postgresql.JSON(), server_default="{}"),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("traces.id"), nullable=True),
        sa.Column("output_preview", sa.Text(), server_default=""),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scenario_job_items")
    op.drop_table("scenario_jobs")
