from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import BookingRead
from app.core.security import assert_owns_or_staff, get_current_user
from app.database import crud
from app.database.models import User
from app.database.session import get_db

router = APIRouter(tags=["bookings"])


@router.get("/bookings/{confirmation_code}", response_model=BookingRead)
def get_booking_by_confirmation_code(
    confirmation_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingRead:
    """Looks up a booking by its human-facing confirmation code - this is
    the one thing a guest types in to submit a review or complaint;
    nothing about the property/host/stay is searched manually (per the
    "system automatically retrieves ... using the Booking ID" workflow).
    """
    booking = crud.get_booking_by_confirmation_code(db, confirmation_code)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_owns_or_staff(booking.guest_id, current_user)
    return booking
