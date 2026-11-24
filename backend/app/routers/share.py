from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import s3
from app.database import get_db
from app.deps import get_optional_user
from app.models import Bucket, File, Folder, User
from app.routers.buckets import (
    BucketOut,
    FileOut,
    FolderOut,
    _bucket_out,
    _file_out,
    _folder_out,
)

router = APIRouter(prefix="/api/share", tags=["share"])


class BucketShareOut(BaseModel):
    bucket: BucketOut
    folders: list[FolderOut]
    files: list[FileOut]
    current_folder: FolderOut | None = None


class FolderShareOut(BaseModel):
    folder: FolderOut
    bucket_name: str
    files: list[FileOut]


class FileShareOut(BaseModel):
    file: FileOut
    bucket_name: str
    folder_name: str
    url: str | None = None


async def _bucket_by_hash(db: AsyncSession, h: str) -> Bucket:
    bucket = (
        await db.execute(select(Bucket).where(Bucket.share_hash == h))
    ).scalar_one_or_none()
    if bucket is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return bucket


def _can_view(bucket: Bucket, user: User | None) -> bool:
    if user is not None and user.uuid == bucket.owner_uuid:
        return True
    return bucket.access in ("public", "link")


def _require(bucket: Bucket, user: User | None) -> None:
    if not _can_view(bucket, user):
        raise HTTPException(status_code=404, detail="Ссылка не найдена")


async def _files_in_folder(db: AsyncSession, folder_uuid: UUID) -> list[File]:
    return list(
        (
            await db.execute(
                select(File)
                .where(File.folder_uuid == folder_uuid)
                .order_by(File.created_at.desc())
            )
        ).scalars()
    )


async def _subfolders(db: AsyncSession, bucket_uuid: UUID) -> list[tuple[Folder, int]]:
    count_subq = (
        select(File.folder_uuid, func.count().label("cnt"))
        .group_by(File.folder_uuid)
        .subquery()
    )
    return list(
        (
            await db.execute(
                select(Folder, func.coalesce(count_subq.c.cnt, 0))
                .join(count_subq, count_subq.c.folder_uuid == Folder.uuid, isouter=True)
                .where(Folder.bucket_uuid == bucket_uuid, Folder.name != "")
                .order_by(Folder.created_at)
            )
        ).all()
    )


async def _root_folder(db: AsyncSession, bucket_uuid: UUID) -> Folder:
    folder = (
        await db.execute(
            select(Folder).where(
                Folder.bucket_uuid == bucket_uuid, Folder.name == ""
            )
        )
    ).scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Содержимое недоступно")
    return folder


@router.get("/b/{h}", response_model=BucketShareOut)
async def share_bucket(
    h: str,
    folder: UUID | None = None,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    bucket = await _bucket_by_hash(db, h)
    _require(bucket, user)

    if folder is None:
        root = await _root_folder(db, bucket.uuid)
        target = root.uuid
        current = None
    else:
        current = await db.get(Folder, folder)
        if current is None or current.bucket_uuid != bucket.uuid:
            raise HTTPException(status_code=404, detail="Папка не найдена")
        if current.name == "":
            current = None
        target = folder

    files = await _files_in_folder(db, target)
    subs = await _subfolders(db, bucket.uuid)

    return BucketShareOut(
        bucket=_bucket_out(bucket),
        folders=[_folder_out(f, c) for f, c in subs],
        files=[_file_out(f) for f in files],
        current_folder=_folder_out(current) if current else None,
    )


@router.get("/a/{h}", response_model=FolderShareOut)
async def share_folder(
    h: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    folder = (
        await db.execute(select(Folder).where(Folder.share_hash == h))
    ).scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    bucket = await db.get(Bucket, folder.bucket_uuid)
    if bucket is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    _require(bucket, user)

    files = await _files_in_folder(db, folder.uuid)
    return FolderShareOut(
        folder=_folder_out(folder, files_count=len(files)),
        bucket_name=bucket.name,
        files=[_file_out(f) for f in files],
    )


@router.get("/f/{h}", response_model=FileShareOut)
async def share_file(
    h: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    file = (
        await db.execute(select(File).where(File.share_hash == h))
    ).scalar_one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    folder = await db.get(Folder, file.folder_uuid)
    if folder is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    bucket = await db.get(Bucket, folder.bucket_uuid)
    if bucket is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    _require(bucket, user)

    url = None
    try:
        key = s3.object_key(
            bucket.owner_uuid, bucket.uuid, folder.uuid, file.uuid, file.extension
        )
        url = s3.presign_get(key, expires=900)
    except Exception:
        url = None

    return FileShareOut(
        file=_file_out(file),
        bucket_name=bucket.name,
        folder_name=folder.name,
        url=url,
    )