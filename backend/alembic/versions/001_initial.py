"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_config", postgresql.JSON(), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), server_default="system"),
        sa.UniqueConstraint("prompt_id", "version_number", name="uq_prompt_version"),
    )

    op.create_index(
        "ix_one_active_per_prompt",
        "prompt_versions",
        ["prompt_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=True),
        sa.Column("input", postgresql.JSON(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("metadata", postgresql.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "replay_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=False),
        sa.Column("target_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("trace_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "replay_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("replay_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("replay_jobs.id"), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("traces.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("original_output", sa.Text(), server_default=""),
        sa.Column("replayed_output", sa.Text(), server_default=""),
        sa.Column("original_score", sa.Float(), nullable=True),
        sa.Column("replayed_score", sa.Float(), nullable=True),
        sa.Column("score_delta", sa.Float(), nullable=True),
        sa.Column("judge_reasoning", sa.Text(), server_default=""),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("replay_results")
    op.drop_table("replay_jobs")
    op.drop_table("traces")
    op.drop_index("ix_one_active_per_prompt", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
