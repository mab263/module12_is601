import logging

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import main
from app.database import Base, engine


def test_tables_are_created_on_startup(monkeypatch):
    calls = []
    monkeypatch.setattr(Base.metadata, "create_all", lambda bind: calls.append(bind))
    with TestClient(main.app):
        pass
    assert calls == [engine]


def test_app_still_starts_when_the_database_is_down(monkeypatch, caplog):
    def fail(bind):
        raise OperationalError("CREATE TABLE users", {}, Exception("connection refused"))

    monkeypatch.setattr(Base.metadata, "create_all", fail)
    with caplog.at_level(logging.WARNING):
        with TestClient(main.app) as client:
            response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "Could not create database tables" in caplog.text