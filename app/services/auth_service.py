"""Auth business logic - the single implementation both the "Login to Give
Feedback" and "Admin Login" frontend pages call through the shared
`POST /auth/login` route. Neither portal gets its own auth logic; they only
differ in copy/branding and in how the frontend redirects based on the
`role` this module returns.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.database import crud
from app.database.models import Role, User

logger = logging.getLogger(__name__)


def register_user(db: Session, *, email: str, password: str, full_name: str | None) -> User:
    if crud.get_user_by_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    # role is never taken from the caller - self-registration is always USER.
    return crud.create_user(db, email=email, hashed_password=hash_password(password), full_name=full_name, role=Role.USER)


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = crud.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")
    return user


def change_password(db: Session, *, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")
    crud.update_user_password(db, user, hash_password(new_password))


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_reset_token(db: Session, *, email: str, settings: Settings) -> str | None:
    """Returns the raw (unhashed) token for the caller to surface/log, or
    None if no account exists for the email - the route must still return
    the same generic response either way, to avoid leaking which emails
    are registered.
    """
    user = crud.get_user_by_email(db, email)
    if user is None:
        return None

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_token_expire_minutes)
    crud.create_password_reset_token(db, user_id=user.id, token_hash=_hash_token(raw_token), expires_at=expires_at)
    return raw_token


def consume_reset_token(db: Session, *, raw_token: str, new_password: str) -> None:
    token = crud.get_valid_reset_token(db, _hash_token(raw_token))
    if token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    user = crud.get_user_by_id(db, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    crud.update_user_password(db, user, hash_password(new_password))
    crud.mark_reset_token_used(db, token)
