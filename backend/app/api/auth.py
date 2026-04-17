from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _to_user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
    )


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    normalized_email = payload.email.strip().lower()

    existing = await db.execute(select(User.id).where(User.email == normalized_email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(access_token=token, user=_to_user_public(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(access_token=token, user=_to_user_public(user))


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return _to_user_public(current_user)
