from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserPublic(BaseModel):
    id: str
    email: str
    full_name: str | None
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("email must be a valid address")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("email must be a valid address")
        return normalized


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
