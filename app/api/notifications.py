from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import NotificationRead
from app.core.security import get_current_user
from app.database import crud
from app.database.models import User
from app.database.session import get_db

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
def list_my_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationRead]:
    return crud.list_notifications_for_user(db, current_user.id, unread_only=unread_only, limit=limit)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    notification = crud.get_notification(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    # Plain per-user ownership, not assert_owns_or_staff - there's no
    # legitimate "staff reads someone else's notifications" case here.
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return crud.mark_notification_read(db, notification)
