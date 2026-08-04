"""Password hashing, JWT issuance/verification, and RBAC dependencies.

Kept in `app/core/` (alongside `config.py`) rather than `app/services/`
since this is cross-cutting infrastructure every router depends on, not
feedback/auth business logic - `app/services/auth_service.py` owns the
latter and calls into this module for the primitives.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database import crud
from app.database.models import Role, User
from app.database.session import get_db

logger = logging.getLogger(__name__)

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed/legacy hash - never let a bad stored value raise past
        # the auth boundary as a 500; it just means the password is wrong.
        return False


def _create_token(*, subject: int, role: Role, expires_delta: timedelta, token_type: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role.value,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user: User, settings: Settings) -> str:
    return _create_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
        settings=settings,
    )


def create_refresh_token(user: User, settings: Settings) -> str:
    return _create_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
        token_type="refresh",
        settings=settings,
    )


def decode_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token, settings)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    user = crud.get_user_by_id(db, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user


def require_role(*roles: Role):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


# Staff tier - provisioned by manual DB promotion, never self-registered.
# Can view every feedback row, analytics, and the weekly report.
STAFF_ROLES = frozenset(
    {Role.SUPPORT_MANAGER, Role.OPS_MANAGER, Role.PRODUCT_MANAGER, Role.TRUST_SAFETY, Role.EXEC}
)

# Subset of STAFF_ROLES that can also write: PATCH feedback, bulk-upload,
# and export CSV/PDF. PRODUCT_MANAGER and EXEC are view-only within staff.
MANAGE_ROLES = frozenset({Role.SUPPORT_MANAGER, Role.OPS_MANAGER})

RequireStaff = require_role(*STAFF_ROLES)
RequireManager = require_role(*MANAGE_ROLES)


def assert_owns_or_staff(owner_user_id: Optional[int], current_user: User) -> None:
    if current_user.role in STAFF_ROLES:
        return
    if owner_user_id is None or owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
