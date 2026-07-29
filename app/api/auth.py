import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.schemas_auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.core.config import Settings, get_settings
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.core.rate_limit import limiter
from app.database import crud
from app.database.models import User
from app.database.session import get_db
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user: User, settings: Settings, *, persistent: bool = True) -> None:
    """`persistent=False` (an unchecked "Remember me") makes the refresh
    cookie a session cookie - no Max-Age, so the browser drops it on
    close, ending the session even though the token itself would
    otherwise still be valid. The access token cookie's short lifetime is
    a security control, not a persistence one, so it always carries its
    own Max-Age regardless.
    """
    access_token = create_access_token(user, settings)
    refresh_token = create_refresh_token(user, settings)
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        max_age=settings.refresh_token_expire_minutes * 60 if persistent else None,
        path="/auth/refresh",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register(
    request: Request,
    payload: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserRead:
    user = auth_service.register_user(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    # Auto-authenticate on signup - avoids a redundant login step right
    # after registering.
    _set_auth_cookies(response, user, settings)
    return user


@router.post("/login", response_model=UserRead)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserRead:
    """Single login endpoint shared by both the "Login to Give Feedback"
    and "Admin Login" frontend pages - they submit to this same route and
    branch their redirect on the returned `role`, never duplicating auth
    logic per portal.
    """
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    _set_auth_cookies(response, user, settings, persistent=payload.remember_me)
    return user


@router.post("/refresh", response_model=UserRead)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserRead:
    """Issues a new access token from the long-lived refresh cookie - kept
    separate from get_current_user, which only accepts access tokens, since
    the whole point of this route is to work after the access token has
    already expired.
    """
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token, settings)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = crud.get_user_by_id(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    _set_auth_cookies(response, user, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/auth/refresh")


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return crud.update_user_profile(db, current_user, full_name=payload.full_name)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ForgotPasswordResponse:
    raw_token = auth_service.generate_reset_token(db, email=payload.email, settings=settings)
    if raw_token is not None:
        logger.info("Password reset token generated for %s", payload.email)
    # Identical response regardless of whether the email exists, to avoid
    # account enumeration. Stub mode: only ever echo the raw token back
    # when DEBUG=true (no real SMTP integration yet); otherwise it's only
    # in the server log above.
    return ForgotPasswordResponse(reset_token=raw_token if settings.debug else None)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.consume_reset_token(db, raw_token=payload.token, new_password=payload.new_password)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    auth_service.change_password(
        db, user=current_user, current_password=payload.current_password, new_password=payload.new_password
    )
