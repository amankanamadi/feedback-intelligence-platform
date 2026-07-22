from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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
    tests never hit OpenAI or ChromaDB. Individual tests can override
    return_value/side_effect on the returned mocks for specific scenarios.
    """
    import app.api.feedback as feedback_module

    classify_mock = MagicMock(return_value=DEFAULT_CLASSIFICATION)
    embedding_mock = MagicMock(return_value=[0.0] * 8)
    retrieve_mock = MagicMock(return_value=[])
    store_mock = MagicMock(return_value=None)

    monkeypatch.setattr(feedback_module, "classify_feedback", classify_mock)
    monkeypatch.setattr(feedback_module, "get_embedding", embedding_mock)
    monkeypatch.setattr(feedback_module, "retrieve_similar_feedback", retrieve_mock)
    monkeypatch.setattr(feedback_module, "store_feedback_embedding", store_mock)

    return {
        "classify": classify_mock,
        "get_embedding": embedding_mock,
        "retrieve": retrieve_mock,
        "store": store_mock,
    }
