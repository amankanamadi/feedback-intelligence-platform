from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.api.sanitization import sanitize_optional_text


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=200)

    @field_validator("full_name", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_optional_text(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    @field_validator("role", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)

    @field_validator("full_name", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_optional_text(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    detail: str = "If an account exists for that email, a password reset link has been generated."
    # Populated only when settings.debug=True, since there is no real SMTP
    # integration yet - never included in a production response.
    reset_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
