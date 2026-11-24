from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="ae-session")


def issue_token(sub: str) -> str:
    return _serializer.dumps({"sub": sub})


def read_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age)
    except BadSignature:
        return None
    sub = data.get("sub")
    return sub if isinstance(sub, str) and sub else None
