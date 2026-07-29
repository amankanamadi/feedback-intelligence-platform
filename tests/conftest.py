from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.ai.schemas import FeedbackClassification
from app.core.config import get_settings
from app.database import models  # noqa: F401  registers models on Base.metadata
from app.database.base import Base
from app.database.models import MainCategory, Priority, Sentiment, SubCategory
from app.database.session import get_db
from app.main import app

# Tests run against a dedicated database, never the one the dashboard/dev
# server points at. Schema is built directly from the ORM models rather
# than replaying Alembic migrations, which is faster and keeps test setup
# independent of migration history (accepting that a model change without
# a matching migration wouldn't be caught here).
TEST_DATABASE_URL = get_settings().database_url.rsplit("/", 1)[0] + "/feedback_intelligence_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def _db_override(db_session):
    """Wires get_db to the test's db_session and resets rate-limit state.

    Split out from `client` so that `client`/`user_client`/`admin_client`
    can each get their OWN TestClient (own cookie jar) while still sharing
    the same db_session - a test requesting more than one of them needs
    genuinely independent authenticated identities, not the same
    connection re-logging-in and clobbering its own cookies.
    """

    def _override_get_db():
        yield db_session

    # Rate-limit counters (app.state.limiter) are process-global and would
    # otherwise leak between tests - a fast pytest run can trip a per-minute
    # auth rate limit purely from unrelated tests sharing the same window.
    app.state.limiter.reset()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(_db_override):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_client(_db_override):
    """An independent TestClient authenticated as a regular USER."""
    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/register", json={"email": "test-user@example.com", "password": "test-password-123"}
        )
        assert response.status_code == 201, response.text
        yield test_client


@pytest.fixture
def admin_client(_db_override, db_session):
    """An independent TestClient authenticated as an ADMIN. Admins are
    never created via self-service registration, so this seeds the row
    directly via crud, matching how a real admin account would be
    provisioned out-of-band.
    """
    from app.core.security import hash_password
    from app.database import crud
    from app.database.models import Role

    crud.create_user(
        db_session, email="test-admin@example.com", hashed_password=hash_password("test-password-123"), role=Role.ADMIN
    )
    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/login", json={"email": "test-admin@example.com", "password": "test-password-123"}
        )
        assert response.status_code == 200, response.text
        yield test_client


DEFAULT_CLASSIFICATION = FeedbackClassification(
    main_category=MainCategory.INCIDENT,
    sub_category=SubCategory.PERFORMANCE_ISSUE,
    sentiment=Sentiment.NEGATIVE,
    themes=["Slow Dashboard", "Performance"],
    priority=Priority.MEDIUM,
    confidence=95,
    summary="Customer reports slow dashboard performance.",
)


@pytest.fixture
def mock_ai(monkeypatch):
    """Patch the AI/embedding calls used by the feedback API route so
    tests never hit OpenAI or Postgres for vector work. Individual tests
    can override return_value/side_effect on the returned mocks for
    specific scenarios.
    """
    import app.api.feedback as feedback_module

    classify_mock = MagicMock(return_value=DEFAULT_CLASSIFICATION)
    embedding_mock = MagicMock(return_value=[0.0] * 1536)
    retrieve_mock = MagicMock(return_value=[])
    store_mock = MagicMock(return_value=None)

    monkeypatch.setattr(feedback_module, "classify_feedback", classify_mock)
    monkeypatch.setattr(feedback_module, "get_embedding", embedding_mock)
    monkeypatch.setattr(feedback_module, "retrieve_similar_feedback", retrieve_mock)
    monkeypatch.setattr(feedback_module.crud, "set_embedding", store_mock)

    return {
        "classify": classify_mock,
        "get_embedding": embedding_mock,
        "retrieve": retrieve_mock,
        "store": store_mock,
    }
