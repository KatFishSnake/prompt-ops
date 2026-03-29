import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Header, HTTPException
from sqlalchemy import select

from .config import settings
from .database import async_session
from .models import User

ALGORITHM = "HS256"
TOKEN_EXPIRY_DAYS = 7


def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(days=TOKEN_EXPIRY_DAYS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def get_current_user(promptops_token: str | None = Cookie(None)) -> User:
    if not promptops_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_jwt(promptops_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


async def get_api_key_user(x_api_key: str | None = Header(None)) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.api_key == x_api_key))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user
