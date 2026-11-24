"""buckets, folders, files

Revision ID: 0002_entities
Revises: 0001_users
Create Date: 2026-01-01 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_entities"
down_revision: Union[str, None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "buckets",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_totp",
            sa.String(length=64),
            sa.ForeignKey("users.totp_secret", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "access",
            sa.String(length=16),
            nullable=False,
            server_default="private",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_buckets_owner_totp", "buckets", ["owner_totp"])

    op.create_table(
        "folders",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column(
            "bucket_uuid",
            sa.Uuid(),
            sa.ForeignKey("buckets.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "bucket_uuid", "name", name="uq_folders_bucket_name"
        ),
    )
    op.create_index("ix_folders_bucket_uuid", "folders", ["bucket_uuid"])

    op.create_table(
        "files",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column(
            "folder_uuid",
            sa.Uuid(),
            sa.ForeignKey("folders.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_files_folder_uuid", "files", ["folder_uuid"])


def downgrade() -> None:
    op.drop_table("files")
    op.drop_table("folders")
    op.drop_table("buckets")
