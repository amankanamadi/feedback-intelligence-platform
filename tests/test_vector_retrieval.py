from app.database import crud
from app.vector_store.retrieval import retrieve_similar_feedback

DIMS = 1536


def _vector(first, second, fill=0.0):
    return [first, second] + [fill] * (DIMS - 2)


def test_retrieve_similar_feedback_excludes_low_similarity_matches(db_session):
    query_embedding = _vector(1.0, 0.0)

    close = crud.create_feedback(db_session, raw_text="Close match.")
    crud.set_embedding(db_session, close, _vector(0.9, 0.1))

    opposite = crud.create_feedback(db_session, raw_text="Opposite meaning.")
    crud.set_embedding(db_session, opposite, _vector(-1.0, 0.0))

    hits = retrieve_similar_feedback(db_session, query_embedding, n_results=5)

    texts = [h["text"] for h in hits]
    assert "Close match." in texts
    assert "Opposite meaning." not in texts


def test_retrieve_similar_feedback_dedupes_identical_text(db_session):
    query_embedding = _vector(1.0, 0.0)

    first = crud.create_feedback(db_session, raw_text="Duplicate text.")
    crud.set_embedding(db_session, first, _vector(0.99, 0.01))

    second = crud.create_feedback(db_session, raw_text="Duplicate text.")
    crud.set_embedding(db_session, second, _vector(0.98, 0.02))

    hits = retrieve_similar_feedback(db_session, query_embedding, n_results=5)

    assert [h["text"] for h in hits].count("Duplicate text.") == 1


def test_retrieve_similar_feedback_excludes_self_via_exclude_id(db_session):
    query_embedding = _vector(1.0, 0.0)
    feedback = crud.create_feedback(db_session, raw_text="Self.")
    crud.set_embedding(db_session, feedback, query_embedding)

    hits = retrieve_similar_feedback(db_session, query_embedding, n_results=5, exclude_id=feedback.id)

    assert hits == []


def test_retrieve_similar_feedback_respects_custom_max_distance(db_session):
    query_embedding = _vector(1.0, 0.0)

    moderate = crud.create_feedback(db_session, raw_text="Moderately related.")
    crud.set_embedding(db_session, moderate, _vector(0.6, 0.8))  # cosine distance = 0.4

    hits_default = retrieve_similar_feedback(db_session, query_embedding, n_results=5)
    assert "Moderately related." in [h["text"] for h in hits_default]

    hits_strict = retrieve_similar_feedback(db_session, query_embedding, n_results=5, max_distance=0.3)
    assert "Moderately related." not in [h["text"] for h in hits_strict]
