from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """Identity: uuid PK; totp_secret is only a login credential."""

    __tablename__ = "users"

    uuid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    totp_secret: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # optional human label; not used for auth
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class Bucket(Base):
    """Ведро — storage space of one user."""

    __tablename__ = "buckets"

    uuid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_uuid: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # one of: public | link | private
    access: Mapped[str] = mapped_column(
        String(16), nullable=False, default="private", server_default="private"
    )
    # short capability id for /b/<hash>
    share_hash: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Folder(Base):
    """Папка внутри ведра; S3-путь: users/<totp>/<bucket>/<folder>/."""

    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("bucket_uuid", "name", name="uq_folders_bucket_name"),
    )

    uuid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    bucket_uuid: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("buckets.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # short capability id for /a/<hash>
    share_hash: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class File(Base):
    """Файл в папке; ключ в S3: users/<totp>/<bucket>/<folder>/<uuid>.<ext>."""

    __tablename__ = "files"

    uuid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    folder_uuid: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("folders.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # human-facing name; S3 key uses uuid + extension only
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # without leading dot, e.g. "png"
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # one of: text | photo | video | other — drives future preview/highlight pipeline
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="other", server_default="other"
    )
    # short capability id for /f/<hash>
    share_hash: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
