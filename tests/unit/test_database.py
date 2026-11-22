import pytest

from app import database


class FakeSession:
    closed = False

    def close(self):
        FakeSession.closed = True


@pytest.fixture(autouse=True)
def reset_fake():
    FakeSession.closed = False


def test_get_db_yields_a_session_and_closes_it(monkeypatch):
    monkeypatch.setattr(database, "SessionLocal", FakeSession)
    generator = database.get_db()
    assert isinstance(next(generator), FakeSession)
    with pytest.raises(StopIteration):
        next(generator)
    assert FakeSession.closed is True


def test_get_db_closes_the_session_when_a_request_fails(monkeypatch):
    monkeypatch.setattr(database, "SessionLocal", FakeSession)
    generator = database.get_db()
    next(generator)
    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("boom"))
    assert FakeSession.closed is True