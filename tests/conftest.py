from contextlib import contextmanager
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
    """An independent TestClient authenticated as a self-registered GUEST
    (the default self-registration role - see UserRegister.role)."""
    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/register", json={"email": "test-user@example.com", "password": "test-password-123"}
        )
        assert response.status_code == 201, response.text
        yield test_client


@pytest.fixture
def host_client(_db_override):
    """An independent TestClient authenticated as a self-registered HOST -
    the other submitter-tier role, still scoped to its own feedback like
    GUEST."""
    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/register",
            json={"email": "test-host@example.com", "password": "test-password-123", "role": "HOST"},
        )
        assert response.status_code == 201, response.text
        yield test_client


@contextmanager
def _make_staff_client(db_session, *, email, role):
    """Shared helper for the staff-tier fixtures below. Staff accounts are
    never created via self-service registration (UserRegister rejects any
    role outside GUEST/HOST), so this seeds the row directly via crud,
    matching how a real staff account would be provisioned out-of-band.
    """
    from app.core.security import hash_password
    from app.database import crud

    crud.create_user(db_session, email=email, hashed_password=hash_password("test-password-123"), role=role)
    with TestClient(app) as test_client:
        response = test_client.post("/auth/login", json={"email": email, "password": "test-password-123"})
        assert response.status_code == 200, response.text
        yield test_client


@pytest.fixture
def admin_client(_db_override, db_session):
    """An independent TestClient authenticated as a SUPPORT_MANAGER - a
    staff role that is both view-all (STAFF_ROLES) and write-capable
    (MANAGE_ROLES), so existing tests written against "admin can do
    everything" keep working unchanged. Kept as `admin_client` (rather
    than renamed to e.g. `support_manager_client`) since most of the
    existing suite just needs "some staff account that can read and
    write", not this specific role.
    """
    from app.database.models import Role

    with _make_staff_client(db_session, email="test-admin@example.com", role=Role.SUPPORT_MANAGER) as test_client:
        yield test_client


@pytest.fixture
def ops_manager_client(_db_override, db_session):
    """Staff + manager tier, like admin_client but under its own distinct
    role - used by RBAC tests that need two *different* manager identities,
    or that want to assert OPS_MANAGER specifically (not just "a manager")
    can write."""
    from app.database.models import Role

    with _make_staff_client(db_session, email="test-ops-manager@example.com", role=Role.OPS_MANAGER) as test_client:
        yield test_client


@pytest.fixture
def product_manager_client(_db_override, db_session):
    """Staff tier, view-only: in STAFF_ROLES but not MANAGE_ROLES. Used by
    RBAC tests asserting that not every staff role can write (PATCH,
    bulk-upload, export)."""
    from app.database.models import Role

    with _make_staff_client(
        db_session, email="test-product-manager@example.com", role=Role.PRODUCT_MANAGER
    ) as test_client:
        yield test_client


@pytest.fixture
def exec_client(_db_override, db_session):
    """Staff tier, view-only: in STAFF_ROLES but not MANAGE_ROLES. See
    product_manager_client - EXEC is the other view-only staff role."""
    from app.database.models import Role

    with _make_staff_client(db_session, email="test-exec@example.com", role=Role.EXEC) as test_client:
        yield test_client


DEFAULT_CLASSIFICATION = FeedbackClassification(
    main_category=MainCategory.GUEST_REVIEW,
    sub_category=SubCategory.CLEANLINESS,
    sentiment=Sentiment.NEGATIVE,
    themes=["Dirty Apartment", "Cleaning Quality"],
    priority=Priority.MEDIUM,
    confidence=95,
    summary="Guest reports the apartment was not clean on arrival.",
    recommended_action="Escalate to the property's housekeeping vendor for a re-clean.",
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
    # get_embedding returns a constant vector for every test, so an
    # unmocked find_duplicate_complaint would run a real, degenerate
    # zero-vector similarity query for any test submitting two same-
    # property items - default it to "no duplicate found".
    duplicate_mock = MagicMock(return_value=None)

    monkeypatch.setattr(feedback_module, "classify_feedback", classify_mock)
    monkeypatch.setattr(feedback_module, "get_embedding", embedding_mock)
    monkeypatch.setattr(feedback_module, "retrieve_similar_feedback", retrieve_mock)
    monkeypatch.setattr(feedback_module, "find_duplicate_complaint", duplicate_mock)
    monkeypatch.setattr(feedback_module.crud, "set_embedding", store_mock)

    return {
        "classify": classify_mock,
        "get_embedding": embedding_mock,
        "retrieve": retrieve_mock,
        "store": store_mock,
        "find_duplicate": duplicate_mock,
    }
