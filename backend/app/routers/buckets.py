from datetime import datetime, timezone
import os
import tempfile
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import s3
from app.database import get_db
from app.deps import get_current_user
from app.models import Bucket, File, Folder, User
from app.share import candidate_hashes

router = APIRouter(prefix="/api", tags=["storage"])

ACCESS_VALUES = {"public", "link", "private"}
TEXT_EXTENSIONS = {
    "txt", "md", "markdown", "json", "csv", "tsv", "xml", "yml", "yaml",
    "js", "jsx", "ts", "tsx", "py", "rb", "go", "rs", "java", "c", "h",
    "cpp", "cs", "sh", "ps1", "bat", "html", "css", "scss", "sql", "log",
    "ini", "cfg", "conf", "toml", "env", "svg",
}


def classify_kind(content_type: str | None, extension: str) -> str:
    ct = (content_type or "").lower()
    ext = extension.lower().lstrip(".")
    if ct.startswith("image/") or ext in {"png", "jpg", "jpeg", "gif", "webp", "avif", "heic", "bmp"}:
        return "photo"
    if ct.startswith("video/") or ext in {"mp4", "webm", "mov", "mkv", "avi", "m4v", "ogv"}:
        return "video"
    if ct.startswith("text/") or ct in {
        "application/json", "application/xml", "application/javascript",
        "application/x-sh", "application/yaml", "application/x-yaml",
        "application/toml", "image/svg+xml",
    }:
        return "text"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "other"


def _extension(original_name: str) -> str:
    return os.path.splitext(original_name)[1].lstrip(".").lower()


async def _owned_bucket(db: AsyncSession, user: User, bucket_uuid: UUID) -> Bucket:
    bucket = await db.get(Bucket, bucket_uuid)
    if bucket is None or bucket.owner_uuid != user.uuid:
        raise HTTPException(status_code=404, detail="Ведро не найдено")
    return bucket


async def _root_folder(db: AsyncSession, bucket_uuid: UUID) -> Folder:
    folder = (
        await db.execute(
            select(Folder).where(
                Folder.bucket_uuid == bucket_uuid, Folder.name == ""
            )
        )
    ).scalar_one_or_none()
    if folder is None:
        folder = Folder(bucket_uuid=bucket_uuid, name="")
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
    return folder


async def _owned_folder(db: AsyncSession, user: User, folder_uuid: UUID) -> Folder:
    folder = await db.get(Folder, folder_uuid)
    if folder is None:
        raise HTTPException(status_code=404, detail="Папка не найдена")
    await _owned_bucket(db, user, folder.bucket_uuid)
    return folder


async def _owned_file(db: AsyncSession, user: User, file_uuid: UUID) -> tuple[File, Folder, Bucket]:
    file = await db.get(File, file_uuid)
    if file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    folder = await db.get(Folder, file.folder_uuid)
    if folder is None:
        raise HTTPException(status_code=404, detail="Папка не найдена")
    bucket = await _owned_bucket(db, user, folder.bucket_uuid)
    return file, folder, bucket


class BucketIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    access: str = "private"


class BucketRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class BucketOut(BaseModel):
    uuid: UUID
    name: str
    access: str
    share_hash: str
    created_at: str

    model_config = {"from_attributes": True}


class FolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderOut(BaseModel):
    uuid: UUID
    name: str
    share_hash: str
    created_at: str
    files_count: int = 0

    model_config = {"from_attributes": True}


class FileOut(BaseModel):
    uuid: UUID
    folder_uuid: UUID
    original_name: str
    extension: str
    content_type: str | None
    size_bytes: int
    kind: str
    share_hash: str
    created_at: str

    model_config = {"from_attributes": True}


class ContentsOut(BaseModel):
    bucket: BucketOut
    folders: list[FolderOut]
    files: list[FileOut]
    current_folder: FolderOut | None


class FileCreateIn(BaseModel):
    folder_uuid: UUID | None = None
    original_name: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    content_type: str | None = Field(default=None, max_length=255)


class UrlOut(BaseModel):
    url: str


class FileMoveIn(BaseModel):
    folder_uuid: UUID


def _iso(value) -> str:
    return value.isoformat()


def _bucket_out(bucket: Bucket) -> BucketOut:
    return BucketOut(
        uuid=bucket.uuid, name=bucket.name, access=bucket.access,
        share_hash=bucket.share_hash, created_at=_iso(bucket.created_at),
    )


def _folder_out(folder: Folder, files_count: int = 0) -> FolderOut:
    return FolderOut(
        uuid=folder.uuid, name=folder.name, share_hash=folder.share_hash,
        created_at=_iso(folder.created_at), files_count=files_count,
    )


def _file_out(file: File) -> FileOut:
    return FileOut(
        uuid=file.uuid, folder_uuid=file.folder_uuid,
        original_name=file.original_name, extension=file.extension,
        content_type=file.content_type, size_bytes=file.size_bytes,
        kind=file.kind, share_hash=file.share_hash,
        created_at=_iso(file.created_at),
    )


@router.get("/buckets", response_model=list[BucketOut])
async def list_buckets(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Bucket).where(Bucket.owner_uuid == user.uuid)
            .order_by(Bucket.created_at)
        )
    ).scalars().all()
    return [_bucket_out(b) for b in rows]


@router.post("/buckets", response_model=BucketOut, status_code=201)
async def create_bucket(
    payload: BucketIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.access not in ACCESS_VALUES:
        raise HTTPException(status_code=400, detail="Недопустимый вид доступа")
    now = datetime.now(timezone.utc)
    bucket_uuid = uuid4()
    bucket = Bucket(
        uuid=bucket_uuid,
        owner_uuid=user.uuid,
        name=payload.name,
        access=payload.access,
        created_at=now,
    )
    bucket.share_hash = candidate_hashes(bucket_uuid, now)[0]
    root_uuid = uuid4()
    root = Folder(uuid=root_uuid, bucket_uuid=bucket_uuid, name="", created_at=now)
    root.share_hash = candidate_hashes(root_uuid, now)[0]
    db.add(bucket)
    db.add(root)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Не удалось создать ссылку")
    await db.commit()
    await db.refresh(bucket)
    return _bucket_out(bucket)


@router.patch("/buckets/{bucket_uuid}", response_model=BucketOut)
async def rename_bucket(
    bucket_uuid: UUID,
    payload: BucketRenameIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bucket = await _owned_bucket(db, user, bucket_uuid)
    bucket.name = payload.name
    await db.commit()
    await db.refresh(bucket)
    return _bucket_out(bucket)


@router.get("/buckets/{bucket_uuid}/contents", response_model=ContentsOut)
async def bucket_contents(
    bucket_uuid: UUID,
    folder: UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bucket = await _owned_bucket(db, user, bucket_uuid)

    count_subq = (
        select(File.folder_uuid, func.count().label("cnt"))
        .group_by(File.folder_uuid)
        .subquery()
    )
    folder_rows = (
        await db.execute(
            select(Folder, func.coalesce(count_subq.c.cnt, 0))
            .join(count_subq, count_subq.c.folder_uuid == Folder.uuid, isouter=True)
            .where(Folder.bucket_uuid == bucket.uuid, Folder.name != "")
            .order_by(Folder.created_at)
        )
    ).all()

    current_folder: Folder | None = None
    if folder is None:
        root = await _root_folder(db, bucket.uuid)
        target_folder_uuid = root.uuid
    else:
        current_folder = await db.get(Folder, folder)
        if current_folder is None or current_folder.bucket_uuid != bucket.uuid:
            raise HTTPException(status_code=404, detail="Папка не найдена")
        if current_folder.name == "":
            current_folder = None
        target_folder_uuid = folder

    files = (
        await db.execute(
            select(File).where(File.folder_uuid == target_folder_uuid)
            .order_by(File.created_at.desc())
        )
    ).scalars().all()

    return ContentsOut(
        bucket=_bucket_out(bucket),
        folders=[_folder_out(f, c) for f, c in folder_rows],
        files=[_file_out(f) for f in files],
        current_folder=_folder_out(current_folder) if current_folder else None,
    )


@router.post("/buckets/{bucket_uuid}/folders", response_model=FolderOut, status_code=201)
async def create_folder(
    bucket_uuid: UUID,
    payload: FolderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_bucket(db, user, bucket_uuid)
    now = datetime.now(timezone.utc)
    folder_uuid = uuid4()
    folder = Folder(uuid=folder_uuid, bucket_uuid=bucket_uuid, name=payload.name, created_at=now)
    folder.share_hash = candidate_hashes(folder_uuid, now)[0]
    db.add(folder)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Папка с таким именем уже есть")
    await db.commit()
    await db.refresh(folder)
    return _folder_out(folder)


@router.delete("/buckets/{bucket_uuid}", status_code=204)
async def delete_bucket(
    bucket_uuid: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bucket = await _owned_bucket(db, user, bucket_uuid)
    prefix = f"users/{user.uuid}/{bucket.uuid}/"
    s3.delete_prefix(prefix)
    await db.delete(bucket)
    await db.commit()


@router.delete("/folders/{folder_uuid}", status_code=204)
async def delete_folder(
    folder_uuid: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folder = await _owned_folder(db, user, folder_uuid)
    if folder.name == "":
        raise HTTPException(status_code=400, detail="Корневую папку нельзя удалить")
    bucket = await _owned_bucket(db, user, folder.bucket_uuid)
    prefix = f"users/{user.uuid}/{bucket.uuid}/{folder.uuid}/"
    s3.delete_prefix(prefix)
    await db.delete(folder)
    await db.commit()


@router.post("/buckets/{bucket_uuid}/files", response_model=FileOut, status_code=201)
async def create_file(
    bucket_uuid: UUID,
    payload: FileCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bucket = await _owned_bucket(db, user, bucket_uuid)

    if payload.folder_uuid is None:
        folder = await _root_folder(db, bucket.uuid)
    else:
        folder = await db.get(Folder, payload.folder_uuid)
        if folder is None or folder.bucket_uuid != bucket.uuid:
            raise HTTPException(status_code=404, detail="Папка не найдена")
        if folder.name == "":
            raise HTTPException(status_code=400, detail="Некорректная папка")

    extension = _extension(payload.original_name)
    kind = classify_kind(payload.content_type, extension)
    now = datetime.now(timezone.utc)
    file_uuid = uuid4()
    file = File(
        uuid=file_uuid,
        folder_uuid=folder.uuid,
        original_name=payload.original_name,
        extension=extension,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        kind=kind,
        created_at=now,
    )
    file.share_hash = candidate_hashes(file_uuid, now)[0]
    db.add(file)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать ссылку")
    await db.commit()
    await db.refresh(file)
    return _file_out(file)


@router.put("/files/{file_uuid}/upload", response_model=FileOut)
async def upload_file(
    file_uuid: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream request body to S3 (browser cannot PUT cross-origin: provider has no CORS API)."""
    file, folder, bucket = await _owned_file(db, user, file_uuid)
    key = s3.object_key(
        user.uuid, bucket.uuid, folder.uuid, file.uuid, file.extension
    )
    with tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024) as tmp:
        async for chunk in request.stream():
            if chunk:
                tmp.write(chunk)
        tmp.seek(0, 2)
        size = tmp.tell()
        tmp.seek(0)
        s3.put_object(key, tmp, content_type=file.content_type, length=size)
    if file.size_bytes != size:
        file.size_bytes = size
        await db.commit()
        await db.refresh(file)
    return _file_out(file)


@router.get("/files/{file_uuid}/url", response_model=UrlOut)
async def file_url(
    file_uuid: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file, folder, bucket = await _owned_file(db, user, file_uuid)
    key = s3.object_key(
        user.uuid, bucket.uuid, folder.uuid, file.uuid, file.extension
    )
    return UrlOut(url=s3.presign_get(key, expires=900))


@router.patch("/files/{file_uuid}", response_model=FileOut)
async def move_file(
    file_uuid: UUID,
    payload: FileMoveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file, folder, bucket = await _owned_file(db, user, file_uuid)
    target = await db.get(Folder, payload.folder_uuid)
    if target is None or target.bucket_uuid != bucket.uuid:
        raise HTTPException(status_code=404, detail="Папка не найдена")
    if target.name == "" or target.uuid == folder.uuid:
        raise HTTPException(status_code=400, detail="Некорректная папка")

    old_key = s3.object_key(
        user.uuid, bucket.uuid, folder.uuid, file.uuid, file.extension
    )
    new_key = s3.object_key(
        user.uuid, bucket.uuid, target.uuid, file.uuid, file.extension
    )
    s3.move(old_key, new_key)
    file.folder_uuid = target.uuid
    await db.commit()
    await db.refresh(file)
    return _file_out(file)


@router.delete("/files/{file_uuid}", status_code=204)
async def delete_file(
    file_uuid: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file, folder, bucket = await _owned_file(db, user, file_uuid)
    key = s3.object_key(
        user.uuid, bucket.uuid, folder.uuid, file.uuid, file.extension
    )
    s3.delete(key)
    await db.delete(file)
    await db.commit()
