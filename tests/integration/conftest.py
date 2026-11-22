"""Fixtures that give integration tests a real Postgres database and an API client."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (importing registers the tables on Base)
from app.database import Base, get_db
from main import app as fastapi_app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def db_engine():
    """Create a fresh set of tables in the test database for the whole run."""
    if not TEST_DATABASE_URL:
        if os.getenv("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI")
        pytest.skip("TEST_DATABASE_URL is not set")

    if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
        pytest.fail("Refusing to run: the test database name must end in '_test'")

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """A session for one test; every table is emptied afterward."""
    session = sessionmaker(bind=db_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with db_engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())


@pytest.fixture
def api_client(db_engine, db_session):
    """A test client whose requests use the test database, with a new session per request."""
    request_session = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db():
        session = request_session()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def validation_status(api_client):
    """The status code this app returns for invalid request data."""
    status_code = api_client.post("/users/login", json={}).status_code
    assert status_code in (400, 422)
    return status_code