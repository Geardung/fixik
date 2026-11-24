"""files.kind — smart upload classification (text|photo|video|other)

Revision ID: 0003_file_kind
Revises: 0002_entities
Create Date: 2026-01-01 00:00:00.000002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_file_kind"
down_revision: Union[str, None] = "0002_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="other",
        ),
    )


def downgrade() -> None:
    op.drop_column("files", "kind")
