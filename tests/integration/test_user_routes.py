import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.security import verify_password

VALID = {"username": "alice", "email": "alice@example.com", "password": "secret123"}
PUBLIC_FIELDS = {"id", "username", "email", "created_at"}


def register(api_client, **overrides):
    return api_client.post("/users/register", json={**VALID, **overrides})


def login(api_client, username="alice", password="secret123"):
    return api_client.post("/users/login", json={"username": username, "password": password})


def stored_users(db_session):
    """Read the users straight from the database, bypassing the API."""
    db_session.expire_all()
    return db_session.scalars(select(User).order_by(User.id)).all()


# ---- registration ----------------------------------------------------------


def test_register_creates_a_user(api_client, db_session):
    response = register(api_client)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == PUBLIC_FIELDS
    assert (body["username"], body["email"]) == ("alice", "alice@example.com")
    users = stored_users(db_session)
    assert [(u.id, u.username, u.email) for u in users] == [
        (body["id"], "alice", "alice@example.com")
    ]


def test_register_response_has_no_password_data(api_client):
    text = register(api_client).text.lower()
    assert "password" not in text
    assert "$2b$" not in text


def test_password_is_stored_as_a_hash(api_client, db_session):
    register(api_client)
    (user,) = stored_users(db_session)
    assert user.password_hash != "secret123"
    assert user.password_hash.startswith("$2")
    assert verify_password("secret123", user.password_hash)
    assert not verify_password("wrong-password", user.password_hash)


def test_register_lowercases_the_email(api_client, db_session):
    response = register(api_client, email="Alice@Example.COM")
    assert response.json()["email"] == "alice@example.com"
    assert stored_users(db_session)[0].email == "alice@example.com"


def test_different_users_can_register(api_client, db_session):
    first = register(api_client)
    second = register(api_client, username="bob", email="bob@example.com")
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["id"] != second.json()["id"]
    assert len(stored_users(db_session)) == 2


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"email": "other@example.com"}, "Username already registered"),
        ({"username": "bob"}, "Email already registered"),
        ({"username": "bob", "email": "ALICE@Example.COM"}, "Email already registered"),
    ],
)
def test_duplicate_users_are_rejected(api_client, db_session, overrides, message):
    register(api_client)
    response = register(api_client, **overrides)
    assert response.status_code == 409
    assert message in response.text
    assert len(stored_users(db_session)) == 1


class NoRows:
    """Pretends the duplicate check found nothing."""

    def first(self):
        return None


def test_a_duplicate_that_slips_past_the_check_is_still_rejected(
    api_client, db_session, monkeypatch
):
    register(api_client)
    with monkeypatch.context() as patch:
        patch.setattr(Session, "scalars", lambda self, *args, **kwargs: NoRows())
        response = register(api_client)
    assert response.status_code == 409
    assert "already registered" in response.text
    assert len(stored_users(db_session)) == 1


@pytest.mark.parametrize(
    "body",
    [
        {**VALID, "email": "not-an-email"},
        {**VALID, "email": "alice@"},
        {**VALID, "username": "ab"},
        {**VALID, "username": "a" * 51},
        {**VALID, "username": "bad name!"},
        {**VALID, "password": "short"},
        {**VALID, "password": "a" * 73},
        {**VALID, "password": "密" * 25},
        {"username": "alice", "email": "alice@example.com"},
        {"username": "alice", "password": "secret123"},
        {"email": "alice@example.com", "password": "secret123"},
        {},
    ],
)
def test_invalid_registrations_are_rejected(api_client, db_session, validation_status, body):
    response = api_client.post("/users/register", json=body)
    assert response.status_code == validation_status
    assert stored_users(db_session) == []


def test_a_body_that_is_not_json_is_rejected(api_client, db_session, validation_status):
    response = api_client.post(
        "/users/register",
        content="this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == validation_status
    assert stored_users(db_session) == []


# ---- login -----------------------------------------------------------------


def test_login_succeeds_with_the_right_password(api_client):
    register(api_client)
    response = login(api_client)
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Login successful"
    assert set(body["user"]) == PUBLIC_FIELDS
    assert body["user"]["username"] == "alice"
    assert "password" not in response.text.lower()


@pytest.mark.parametrize("identifier", ["alice", "alice@example.com", "ALICE@Example.COM"])
def test_login_accepts_a_username_or_an_email(api_client, identifier):
    register(api_client)
    assert login(api_client, username=identifier).status_code == 200


def test_login_returns_the_matching_user(api_client):
    alice = register(api_client).json()
    bob = register(
        api_client, username="bob", email="bob@example.com", password="another-pass1"
    ).json()
    response = login(api_client, username="bob", password="another-pass1")
    assert response.json()["user"]["id"] == bob["id"]
    assert response.json()["user"]["id"] != alice["id"]


@pytest.mark.parametrize("password", ["wrong-password", "Secret123", "secret123 ", "a" * 100])
def test_wrong_passwords_are_rejected(api_client, password):
    register(api_client)
    response = login(api_client, password=password)
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_unknown_users_are_rejected(api_client):
    response = login(api_client, username="nobody")
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_unknown_user_and_wrong_password_look_the_same(api_client):
    register(api_client)
    wrong_password = login(api_client, password="wrong-password")
    unknown_user = login(api_client, username="nobody")
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.text == unknown_user.text


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"username": "alice"},
        {"password": "secret123"},
        {"username": "", "password": "secret123"},
        {"username": "alice", "password": ""},
        {"username": "a" * 256, "password": "secret123"},
    ],
)
def test_invalid_login_requests_are_rejected(api_client, validation_status, body):
    register(api_client)
    assert api_client.post("/users/login", json=body).status_code == validation_status


def test_login_does_not_change_the_stored_user(api_client, db_session):
    register(api_client)
    snapshot = [(u.id, u.username, u.email, u.password_hash) for u in stored_users(db_session)]
    login(api_client)
    login(api_client, password="wrong-password")
    after = [(u.id, u.username, u.email, u.password_hash) for u in stored_users(db_session)]
    assert after == snapshot