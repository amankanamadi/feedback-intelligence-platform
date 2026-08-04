from app.database import crud
from app.database.models import Property, PropertyType
from app.vector_store.retrieval import find_duplicate_complaint

EMBEDDING_DIMENSIONS = 1536


def _one_hot(index: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


def _seed_property(db_session, **overrides) -> Property:
    defaults = dict(
        name="Duplicate Test Loft", host_name="Test Host", city="Denver", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def test_find_duplicate_complaint_matches_near_identical_same_property(db_session):
    property_row = _seed_property(db_session)
    existing = crud.create_feedback(db_session, raw_text="The lock is broken.", property_id=property_row.id)
    existing.embedding = _one_hot(0)
    db_session.commit()

    new_item = crud.create_feedback(db_session, raw_text="The lock is still broken.", property_id=property_row.id)

    match = find_duplicate_complaint(
        db_session, _one_hot(0), property_id=property_row.id, exclude_id=new_item.id
    )

    assert match is not None
    assert match["id"] == existing.id
    assert match["distance"] < 0.01


def test_find_duplicate_complaint_returns_none_for_distant_vector(db_session):
    property_row = _seed_property(db_session)
    existing = crud.create_feedback(db_session, raw_text="The lock is broken.", property_id=property_row.id)
    existing.embedding = _one_hot(0)
    db_session.commit()

    new_item = crud.create_feedback(db_session, raw_text="Totally unrelated feedback.", property_id=property_row.id)

    match = find_duplicate_complaint(
        db_session, _one_hot(1), property_id=property_row.id, exclude_id=new_item.id
    )

    assert match is None


def test_find_duplicate_complaint_scoped_to_same_property(db_session):
    property_a = _seed_property(db_session, name="Property A")
    property_b = _seed_property(db_session, name="Property B")
    existing = crud.create_feedback(db_session, raw_text="The lock is broken.", property_id=property_a.id)
    existing.embedding = _one_hot(0)
    db_session.commit()

    new_item = crud.create_feedback(db_session, raw_text="The lock is broken here too.", property_id=property_b.id)

    match = find_duplicate_complaint(
        db_session, _one_hot(0), property_id=property_b.id, exclude_id=new_item.id
    )

    assert match is None


def test_duplicate_of_feedback_id_wired_into_api_response(admin_client, mock_ai, db_session):
    property_row = _seed_property(db_session)

    first = admin_client.post(
        "/feedback", json={"raw_text": "The smoke detector is missing.", "property_id": property_row.id}
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    mock_ai["find_duplicate"].return_value = {"id": first_id, "distance": 0.05}

    second = admin_client.post(
        "/feedback", json={"raw_text": "The smoke detector is still missing.", "property_id": property_row.id}
    )

    assert second.status_code == 201
    assert second.json()["duplicate_of_feedback_id"] == first_id
