from app.database.models import Property, PropertyType


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
