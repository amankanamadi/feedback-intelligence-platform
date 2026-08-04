from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import WishlistRead
from app.core.security import require_role
from app.database import crud
from app.database.models import Role, User
from app.database.session import get_db

router = APIRouter(tags=["wishlist"])

# Wishlist.guest_id is a guest concept by construction (see the model's
# own FK naming) - not the broader SUBMITTER_ROLES (GUEST+HOST).
RequireGuest = require_role(Role.GUEST)


@router.get("/wishlist", response_model=list[WishlistRead])
def list_my_wishlist(
    current_user: User = Depends(RequireGuest),
    db: Session = Depends(get_db),
) -> list[WishlistRead]:
    items = crud.list_wishlist_for_guest(db, current_user.id)
    ratings = crud.get_property_average_ratings(db, [item.property_id for item in items])
    shaped = []
    for item in items:
        wishlist_read = WishlistRead.model_validate(item)
        wishlist_read.property.average_rating = ratings.get(item.property_id)
        shaped.append(wishlist_read)
    return shaped


@router.post("/wishlist/{property_id}", response_model=WishlistRead)
def add_wishlist_item(
    property_id: int,
    current_user: User = Depends(RequireGuest),
    db: Session = Depends(get_db),
) -> WishlistRead:
    if crud.get_property(db, property_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    item = crud.add_to_wishlist(db, guest_id=current_user.id, property_id=property_id)
    ratings = crud.get_property_average_ratings(db, [property_id])
    wishlist_read = WishlistRead.model_validate(item)
    wishlist_read.property.average_rating = ratings.get(property_id)
    return wishlist_read


@router.delete("/wishlist/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_wishlist_item(
    property_id: int,
    current_user: User = Depends(RequireGuest),
    db: Session = Depends(get_db),
) -> None:
    crud.remove_from_wishlist(db, guest_id=current_user.id, property_id=property_id)
