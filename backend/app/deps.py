from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.security import read_token


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    sub = read_token(token)
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid session")
    try:
        user = await db.get(User, UUID(sub))
    except ValueError:
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
