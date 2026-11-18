"""
Auth service — registration, login, JWT issuance.
All business logic lives here; routes stay thin.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthError(HTTPException):
    def __init__(self, detail: str, code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=code, detail=detail)


async def register(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None,
) -> User:
    repo = UserRepository(db)
    existing = await repo.get_by_email(email)
    if existing:
        raise AuthError("Email already registered", status.HTTP_409_CONFLICT)
    user = await repo.create(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
    )
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password", status.HTTP_401_UNAUTHORIZED)
    return user


async def issue_token_for(user: User) -> str:
    return create_access_token(subject=str(user.id), extra={"email": user.email})


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    import uuid
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    repo = UserRepository(db)
    return await repo.get_by_id(uid)
