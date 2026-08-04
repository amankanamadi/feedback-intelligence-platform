from app.database.models import Property, PropertyType


def _seed_property(db_session, **overrides) -> Property:
    defaults = dict(
        name="Sunny Loft", host_name="Jordan Lee", city="Austin", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def test_wishlist_requires_authentication(client, db_session):
    property_row = _seed_property(db_session)

    assert client.get("/wishlist").status_code == 401
    assert client.post(f"/wishlist/{property_row.id}").status_code == 401
    assert client.delete(f"/wishlist/{property_row.id}").status_code == 401


def test_host_forbidden_from_wishlist_endpoints(host_client, db_session):
    property_row = _seed_property(db_session)

    assert host_client.get("/wishlist").status_code == 403
    assert host_client.post(f"/wishlist/{property_row.id}").status_code == 403
    assert host_client.delete(f"/wishlist/{property_row.id}").status_code == 403


def test_staff_forbidden_from_wishlist_endpoints(admin_client, db_session):
    property_row = _seed_property(db_session)

    assert admin_client.get("/wishlist").status_code == 403
    assert admin_client.post(f"/wishlist/{property_row.id}").status_code == 403
    assert admin_client.delete(f"/wishlist/{property_row.id}").status_code == 403


def test_guest_can_add_and_list_wishlist_item(user_client, db_session):
    property_row = _seed_property(db_session)

    add_response = user_client.post(f"/wishlist/{property_row.id}")
    assert add_response.status_code == 200
    body = add_response.json()
    assert body["property"]["id"] == property_row.id

    list_response = user_client.get("/wishlist")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["property"]["name"] == "Sunny Loft"


def test_adding_twice_is_idempotent(user_client, db_session):
    property_row = _seed_property(db_session)

    first = user_client.post(f"/wishlist/{property_row.id}")
    second = user_client.post(f"/wishlist/{property_row.id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    items = user_client.get("/wishlist").json()
    assert len(items) == 1


def test_add_wishlist_404_for_unknown_property(user_client):
    response = user_client.post("/wishlist/999999")

    assert response.status_code == 404


def test_guest_can_remove_wishlist_item(user_client, db_session):
    property_row = _seed_property(db_session)
    user_client.post(f"/wishlist/{property_row.id}")

    remove_response = user_client.delete(f"/wishlist/{property_row.id}")

    assert remove_response.status_code == 204
    assert user_client.get("/wishlist").json() == []


def test_removing_nonexistent_item_is_a_noop(user_client, db_session):
    property_row = _seed_property(db_session)

    response = user_client.delete(f"/wishlist/{property_row.id}")

    assert response.status_code == 204


def test_wishlist_isolated_between_guests(user_client, host_client, db_session):
    # host_client stands in for "a different guest identity" here purely
    # to get a second independent authenticated session - the assertion
    # itself is about wishlist isolation, not host-vs-guest semantics.
    from app.core.security import hash_password
    from app.database import crud
    from app.database.models import Role

    other_guest_id = crud.create_user(
        db_session, email="other-guest@example.com", hashed_password=hash_password("test-password-123"),
        role=Role.GUEST,
    ).id

    property_row = _seed_property(db_session)
    crud.add_to_wishlist(db_session, guest_id=other_guest_id, property_id=property_row.id)

    response = user_client.get("/wishlist")

    assert response.status_code == 200
    assert response.json() == []


def test_wishlist_average_rating_reflects_guest_ratings(user_client, db_session):
    from app.database import crud

    property_row = _seed_property(db_session)
    crud.create_feedback(db_session, raw_text="Great stay.", property_id=property_row.id, overall_rating=4)

    response = user_client.post(f"/wishlist/{property_row.id}")

    assert response.status_code == 200
    assert response.json()["property"]["average_rating"] == 4.0
