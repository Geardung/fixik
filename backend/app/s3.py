from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.config import settings


class S3NotConfigured(RuntimeError):
    pass


def _key(key: str) -> str:
    return key.lstrip("/")


def object_key(
    user_uuid: str, bucket_uuid: str, folder_uuid: str, file_uuid: str, extension: str
) -> str:
    """users/<user_uuid>/<bucket_uuid>/<folder_uuid>/<file_uuid>[.<ext>]"""
    ext = extension.lstrip(".")
    base = f"users/{user_uuid}/{bucket_uuid}/{folder_uuid}/{file_uuid}"
    return f"{base}.{ext}" if ext else base


@lru_cache
def get_client() -> BaseClient:
    if not settings.s3_bucket or not settings.s3_access_key_id:
        raise S3NotConfigured("S3 is not configured (S3_BUCKET / S3_ACCESS_KEY_ID)")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def presign_get(key: str, expires: int = 3600) -> str:
    return get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": _key(key)},
        ExpiresIn=expires,
    )


def presign_put(key: str, expires: int = 3600, content_type: str | None = None) -> str:
    params: dict = {"Bucket": settings.s3_bucket, "Key": _key(key)}
    if content_type:
        params["ContentType"] = content_type
    return get_client().generate_presigned_url(
        "put_object", Params=params, ExpiresIn=expires
    )


def put_object(
    key: str, body, content_type: str | None = None, length: int | None = None
) -> None:
    params: dict = {"Bucket": settings.s3_bucket, "Key": _key(key), "Body": body}
    if content_type:
        params["ContentType"] = content_type
    if length is not None:
        params["ContentLength"] = length
    get_client().put_object(**params)


def exists(key: str) -> bool:
    try:
        get_client().head_object(Bucket=settings.s3_bucket, Key=_key(key))
        return True
    except ClientError as e:
        code = str(e.response.get("Error", {}).get("Code", ""))
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in ("404", "NoSuchKey", "NotFound") or status == 404:
            return False
        raise


def delete(key: str) -> None:
    get_client().delete_object(Bucket=settings.s3_bucket, Key=_key(key))


def delete_prefix(prefix: str) -> int:
    """Delete all objects under prefix; returns number of keys removed."""
    client = get_client()
    bucket = settings.s3_bucket
    removed = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=_key(prefix)):
        contents = page.get("Contents", [])
        if not contents:
            continue
        for i in range(0, len(contents), 1000):
            batch = contents[i : i + 1000]
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in batch], "Quiet": True},
            )
            removed += len(batch)
    return removed


def move(src: str, dst: str) -> None:
    src, dst = _key(src), _key(dst)
    if src == dst:
        return
    client = get_client()
    bucket = settings.s3_bucket
    client.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": src},
        Key=dst,
    )
    client.delete_object(Bucket=bucket, Key=src)


def list_keys(prefix: str = "") -> list[str]:
    client = get_client()
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=_key(prefix)):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return keys
