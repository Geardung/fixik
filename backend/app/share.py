import hashlib
from datetime import datetime
from uuid import UUID

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _encode(n: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(ALPHABET[n % 62])
        n //= 62
    return "".join(reversed(chars))


def share_hash(object_uuid: UUID, created_at: datetime, length: int = 8) -> str:
    """Short capability id: hash(object_uuid, create_time) → 8–10 base62 chars."""
    payload = f"{object_uuid.hex}:{created_at.isoformat()}".encode()
    digest = hashlib.blake2b(payload, digest_size=16).digest()
    return _encode(int.from_bytes(digest, "big"), length)


def candidate_hashes(object_uuid: UUID, created_at: datetime) -> list[str]:
    """Ordered candidates: prefer 8, then 10 — for unique-collision retries."""
    return [
        share_hash(object_uuid, created_at, 8),
        share_hash(object_uuid, created_at, 10),
        share_hash(object_uuid, created_at, 12),
    ]
