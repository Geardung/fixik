from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pyotp

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.names import random_display_name
from app.security import issue_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class StartResponse(BaseModel):
    secret: str
    otpauth_url: str


class CodePayload(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=6, max_length=6)


class UserOut(BaseModel):
    totp_secret: str
    display_name: str | None = None


def _set_session(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.session_cookie,
        value=issue_token(str(user.uuid)),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
    )


def _clear_session(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie, path="/")


def _claim_first_login(user: User) -> bool:
    """First successful auth: stamp a random display_name (marks TOTP as ever authorized)."""
    if user.display_name:
        return False
    user.display_name = random_display_name()
    return True


def _code_matches(secret: str, code: str) -> bool:
    try:
        return bool(pyotp.TOTP(secret).verify(code, valid_window=1))
    except Exception:
        return False


@router.post("/start", response_model=StartResponse)
async def start():
    """Fresh random TOTP secret for the QR (register fallback / first scan)."""
    secret = pyotp.random_base32(length=32)
    totp = pyotp.TOTP(secret)
    return StartResponse(
        secret=secret,
        otpauth_url=totp.provisioning_uri(name="ae", issuer_name="ae"),
    )


@router.post("/verify", response_model=UserOut)
async def verify(
    payload: CodePayload, response: Response, db: AsyncSession = Depends(get_db)
):
    """One-shot auth: match code against DB users, else claim the QR secret."""
    code = payload.code
    rows = (await db.execute(select(User))).scalars().all()
    matches = [u for u in rows if _code_matches(u.totp_secret, code)]

    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Код подходит нескольким аккаунтам")

    if len(matches) == 1:
        user = matches[0]
    else:
        if not _code_matches(payload.secret, code):
            raise HTTPException(status_code=400, detail="Неверный код")
        existing = (
            await db.execute(
                select(User).where(User.totp_secret == payload.secret)
            )
        ).scalar_one_or_none()
        if existing is not None:
            user = existing
        else:
            user = User(totp_secret=payload.secret)
            _claim_first_login(user)
            db.add(user)
            await db.commit()
            await db.refresh(user)

    if _claim_first_login(user):
        await db.commit()
        await db.refresh(user)

    _set_session(response, user)
    return UserOut(totp_secret=user.totp_secret, display_name=user.display_name)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    _clear_session(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(totp_secret=user.totp_secret, display_name=user.display_name)
