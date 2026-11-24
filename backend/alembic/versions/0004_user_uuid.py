"""users.uuid as PK; buckets.owner_uuid replaces owner_totp

Revision ID: 0004_user_uuid
Revises: 0003_file_kind
Create Date: 2026-01-01 00:00:00.000003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_user_uuid"
down_revision: Union[str, None] = "0003_file_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) uuid column + temporary unique (FK target needs unique BEFORE PK swap)
    op.execute("ALTER TABLE users ADD COLUMN uuid uuid")
    op.execute("UPDATE users SET uuid = gen_random_uuid() WHERE uuid IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN uuid SET NOT NULL")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_uuid_key UNIQUE (uuid)")

    # 2) buckets: move ownership to users.uuid, drop old FK first
    #    (old FK depends on users_pkey, blocks the PK swap below)
    op.execute("ALTER TABLE buckets ADD COLUMN owner_uuid uuid")
    op.execute(
        """
        UPDATE buckets b
        SET owner_uuid = u.uuid
        FROM users u
        WHERE b.owner_totp = u.totp_secret
        """
    )
    op.execute("DELETE FROM buckets WHERE owner_uuid IS NULL")
    op.execute("ALTER TABLE buckets ALTER COLUMN owner_uuid SET NOT NULL")
    op.execute(
        """
        ALTER TABLE buckets
        ADD CONSTRAINT buckets_owner_uuid_fkey
        FOREIGN KEY (owner_uuid) REFERENCES users(uuid) ON DELETE CASCADE
        """
    )
    op.execute("ALTER TABLE buckets DROP COLUMN owner_totp")

    # 3) swap users PK to uuid
    #    (users_uuid_key stays: buckets_owner_uuid_fkey references it)
    op.execute("ALTER TABLE users DROP CONSTRAINT users_pkey")
    op.execute("ALTER TABLE users ADD PRIMARY KEY (uuid)")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_totp_secret_key UNIQUE (totp_secret)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE buckets ADD COLUMN owner_totp varchar(64)")
    op.execute(
        """
        UPDATE buckets b
        SET owner_totp = u.totp_secret
        FROM users u
        WHERE b.owner_uuid = u.uuid
        """
    )
    op.execute("ALTER TABLE buckets ALTER COLUMN owner_totp SET NOT NULL")
    op.execute(
        """
        ALTER TABLE buckets
        ADD CONSTRAINT buckets_owner_totp_fkey
        FOREIGN KEY (owner_totp) REFERENCES users(totp_secret) ON DELETE CASCADE
        """
    )
    op.execute("ALTER TABLE buckets DROP CONSTRAINT buckets_owner_uuid_fkey")
    op.execute("ALTER TABLE buckets DROP COLUMN owner_uuid")

    op.execute("ALTER TABLE users ADD CONSTRAINT users_uuid_key UNIQUE (uuid)")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_pkey")
    op.execute("ALTER TABLE users ADD PRIMARY KEY (totp_secret)")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_uuid_key")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_totp_secret_key")
    op.execute("ALTER TABLE users DROP COLUMN uuid")
