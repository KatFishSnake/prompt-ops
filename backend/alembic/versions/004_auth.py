"""add auth: users table, user_id on models, composite name constraint

Revision ID: 004
Revises: 003
Create Date: 2024-01-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("api_key", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add user_id to prompts
    op.add_column("prompts", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    # Drop old unique constraint on name, add composite
    op.drop_constraint("prompts_name_key", "prompts", type_="unique")
    op.create_unique_constraint("uq_prompt_name_user", "prompts", ["name", "user_id"])

    # Add user_id to traces
    op.add_column("traces", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))

    # Add user_id to replay_jobs
    op.add_column("replay_jobs", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))

    # Add user_id to scenario_jobs
    op.add_column("scenario_jobs", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("scenario_jobs", "user_id")
    op.drop_column("replay_jobs", "user_id")
    op.drop_column("traces", "user_id")
    op.drop_constraint("uq_prompt_name_user", "prompts", type_="unique")
    op.add_column("prompts", sa.Column("name", sa.String(255), unique=True))
    op.drop_column("prompts", "user_id")
    op.drop_table("users")
