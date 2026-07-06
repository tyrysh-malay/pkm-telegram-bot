"""add artifact git commit sha

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("git_commit_sha", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("artifacts", "git_commit_sha")
