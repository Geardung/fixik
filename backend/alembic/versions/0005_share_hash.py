"""share_hash on buckets, folders, files

Revision ID: 0005_share_hash
Revises: 0004_user_uuid
Create Date: 2026-01-01 00:00:00.000004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.share import candidate_hashes

revision: str = "0005_share_hash"
down_revision: Union[str, None] = "0004_user_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill(table: str) -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(f"SELECT uuid, created_at FROM {table} WHERE share_hash IS NULL")
    ).fetchall()
    for uuid_val, created_at in rows:
        for h in candidate_hashes(uuid_val, created_at):
            try:
                conn.execute(
                    sa.text(
                        f"UPDATE {table} SET share_hash = :h WHERE uuid = :u"
                    ),
                    {"h": h, "u": uuid_val},
                )
                break
            except Exception:
                conn.rollback()
                raise


def upgrade() -> None:
    for table in ("buckets", "folders", "files"):
        op.add_column(
            table, sa.Column("share_hash", sa.String(length=16), nullable=True)
        )
        _backfill(table)
        op.alter_column(
            table, "share_hash", existing_type=sa.String(length=16), nullable=False
        )
        op.create_unique_constraint(
            f"uq_{table}_share_hash", table, ["share_hash"]
        )


def downgrade() -> None:
    for table in ("buckets", "folders", "files"):
        op.drop_constraint(f"uq_{table}_share_hash", table, type_="unique")
        op.drop_column(table, "share_hash")
