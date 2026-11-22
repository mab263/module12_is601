from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import LoginResponse, UserLogin, UserRead


def test_valid_login_data():
    login = UserLogin(username="alice", password="secret123")
    assert (login.username, login.password) == ("alice", "secret123")


def test_an_email_address_is_accepted_as_the_username():
    assert UserLogin(username="alice@example.com", password="x").username == "alice@example.com"


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"username": "alice"},
        {"password": "secret123"},
        {"username": "", "password": "secret123"},
        {"username": "alice", "password": ""},
        {"username": "a" * 256, "password": "secret123"},
    ],
)
def test_invalid_login_data_is_rejected(data):
    with pytest.raises(ValidationError):
        UserLogin(**data)


def test_login_response_carries_only_public_user_details():
    user = UserRead.model_validate(
        SimpleNamespace(
            id=1,
            username="alice",
            email="alice@example.com",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    response = LoginResponse(message="Login successful", user=user)
    assert set(response.model_dump()) == {"message", "user"}
    assert set(response.model_dump()["user"]) == {"id", "username", "email", "created_at"}
    assert "password" not in response.model_dump_json()