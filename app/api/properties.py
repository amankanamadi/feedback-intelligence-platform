from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import PropertyRead
from app.core.security import get_current_user
from app.database import crud
from app.database.models import User
from app.database.session import get_db

router = APIRouter(tags=["properties"])


@router.get("/properties", response_model=list[PropertyRead])
def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    city: Optional[str] = Query(None, min_length=1, max_length=100),
    host_id: Optional[int] = Query(None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PropertyRead]:
    # Static reference data, open to any authenticated user - guests/hosts
    # need this list to pick a property when submitting feedback. host_id
    # discloses nothing new - host_name is already visible on every
    # unfiltered row - it just lets a host ask for "my own".
    properties = crud.list_properties(db, skip=skip, limit=limit, search=search, city=city, host_id=host_id)
    # average_rating isn't a Property column, so from_attributes can't pick
    # it up - computed from guest-submitted ratings only (never AI) and
    # filled in here, same pattern as FeedbackSubmitterRead.property_name.
    ratings = crud.get_property_average_ratings(db, [p.id for p in properties])
    shaped = []
    for property_row in properties:
        item = PropertyRead.model_validate(property_row)
        item.average_rating = ratings.get(property_row.id)
        shaped.append(item)
    return shaped
