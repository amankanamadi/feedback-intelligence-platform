from app.core.security import hash_password
from app.database import crud
from app.database.models import Property, PropertyType, Role


def _seed_host_user(db_session, *, email):
    return crud.create_user(
        db_session, email=email, hashed_password=hash_password("test-password-123"), role=Role.HOST
    ).id


def _seed_properties(db_session):
    properties = [
        Property(
            name="Sunny Loft", host_name="Jordan Lee", city="Austin", country="USA",
            property_type=PropertyType.ENTIRE_HOME,
        ),
        Property(
            name="Cozy Studio", host_name="Alex Rivera", city="Denver", country="USA",
            property_type=PropertyType.PRIVATE_ROOM,
        ),
        Property(
            name="Shared Downtown Flat", host_name="Jordan Lee", city="Austin", country="USA",
            property_type=PropertyType.SHARED_ROOM,
        ),
    ]
    db_session.add_all(properties)
    db_session.commit()
    return properties


def test_list_properties_returns_all_for_authenticated_user(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {item["name"] for item in body} == {"Sunny Loft", "Cozy Studio", "Shared Downtown Flat"}
    assert body[0]["property_type"] in {"Entire Home", "Private Room", "Shared Room"}


def test_list_properties_requires_authentication(client, db_session):
    _seed_properties(db_session)

    response = client.get("/properties")

    assert response.status_code == 401


def test_list_properties_filters_by_search(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties", params={"search": "sunny"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Sunny Loft"


def test_list_properties_search_matches_city(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties", params={"search": "denver"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Cozy Studio"


def test_list_properties_filters_by_city(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties", params={"city": "austin"})

    assert response.status_code == 200
    body = response.json()
    assert {item["name"] for item in body} == {"Sunny Loft", "Shared Downtown Flat"}


def test_list_properties_respects_pagination(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties", params={"skip": 1, "limit": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_properties_empty_when_no_properties_seeded(user_client):
    response = user_client.get("/properties")

    assert response.status_code == 200
    assert response.json() == []


def test_list_properties_filters_by_host_id(user_client, db_session):
    host_id = _seed_host_user(db_session, email="host-a@example.com")
    other_host_id = _seed_host_user(db_session, email="host-b@example.com")
    owned = Property(
        name="My Listing", host_name="Jordan Lee", host_id=host_id, city="Austin", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    other = Property(
        name="Someone Else's Listing", host_name="Alex Rivera", host_id=other_host_id, city="Denver", country="USA",
        property_type=PropertyType.PRIVATE_ROOM,
    )
    db_session.add_all([owned, other])
    db_session.commit()

    response = user_client.get("/properties", params={"host_id": host_id})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "My Listing"


def test_list_properties_host_id_combines_with_search_as_and(user_client, db_session):
    host_id = _seed_host_user(db_session, email="host-a@example.com")
    other_host_id = _seed_host_user(db_session, email="host-b@example.com")
    matching = Property(
        name="Sunny Spot", host_name="Jordan Lee", host_id=host_id, city="Austin", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    wrong_host = Property(
        name="Sunny Cabin", host_name="Alex Rivera", host_id=other_host_id, city="Denver", country="USA",
        property_type=PropertyType.PRIVATE_ROOM,
    )
    right_host_no_match = Property(
        name="Rainy Studio", host_name="Jordan Lee", host_id=host_id, city="Austin", country="USA",
        property_type=PropertyType.SHARED_ROOM,
    )
    db_session.add_all([matching, wrong_host, right_host_no_match])
    db_session.commit()

    response = user_client.get("/properties", params={"host_id": host_id, "search": "sunny"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Sunny Spot"


def test_list_properties_unknown_host_id_returns_empty(user_client, db_session):
    _seed_properties(db_session)

    response = user_client.get("/properties", params={"host_id": 999999})

    assert response.status_code == 200
    assert response.json() == []


def test_submit_feedback_with_invalid_property_id_returns_404(user_client, mock_ai):
    response = user_client.post(
        "/feedback", json={"raw_text": "Feedback about a property that doesn't exist.", "property_id": 999999}
    )

    assert response.status_code == 404
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_with_valid_property_id_succeeds(user_client, db_session, mock_ai):
    (property_row,) = _seed_properties(db_session)[:1]

    response = user_client.post(
        "/feedback", json={"raw_text": "Loved staying at this listing!", "property_id": property_row.id}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["property_id"] == property_row.id
    assert body["property_name"] == "Sunny Loft"
    assert body["property_city"] == "Austin"


def test_get_property_returns_expected_shape(user_client, db_session):
    (property_row,) = _seed_properties(db_session)[:1]

    response = user_client.get(f"/properties/{property_row.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == property_row.id
    assert body["name"] == "Sunny Loft"
    assert body["city"] == "Austin"
    assert body["country"] == "USA"
    assert body["property_type"] == "Entire Home"
    assert body["average_rating"] is None


def test_get_property_404_for_unknown_id(user_client):
    response = user_client.get("/properties/999999")

    assert response.status_code == 404


def test_get_property_requires_authentication(client, db_session):
    (property_row,) = _seed_properties(db_session)[:1]

    response = client.get(f"/properties/{property_row.id}")

    assert response.status_code == 401
