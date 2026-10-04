"""Add tenant workspace revision counter for live application updates."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6bc1d4a21f30"
down_revision: Union[str, None] = "afab94e177f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("workspace_revision", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("organizations", "workspace_revision")
