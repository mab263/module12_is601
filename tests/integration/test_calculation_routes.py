import pytest
from sqlalchemy import select

from app.models import Calculation, User
from app.security import hash_password

FIELDS = {"id", "a", "b", "type", "result", "user_id", "created_at"}

INVALID_BODIES = [
    {"a": 1, "b": 0, "type": "Divide"},
    {"a": 1, "b": 0, "type": "divide"},
    {"a": 1, "b": 2, "type": "Power"},
    {"a": "abc", "b": 2, "type": "Add"},
    {"a": None, "b": 2, "type": "Add"},
    {"a": 1, "type": "Add"},
    {"b": 2, "type": "Add"},
    {"a": 1, "b": 2},
    {"a": 1, "b": 2, "type": 5},
    {},
]


def create(api_client, calculation_type="Add", a=2, b=3):
    return api_client.post("/calculations", json={"a": a, "b": b, "type": calculation_type})


def stored(db_session):
    """Read the calculations straight from the database, bypassing the API."""
    db_session.expire_all()
    return db_session.scalars(select(Calculation).order_by(Calculation.id)).all()


def snapshot(db_session):
    return [(c.id, c.a, c.b, c.type, c.result) for c in stored(db_session)]


# ---- Add -------------------------------------------------------------------


@pytest.mark.parametrize(
    "calculation_type, a, b, expected",
    [("Add", 2, 3, 5), ("Sub", 5, 3, 2), ("Multiply", 4, 5, 20), ("Divide", 10, 4, 2.5)],
)
def test_add_creates_a_calculation(api_client, db_session, calculation_type, a, b, expected):
    response = create(api_client, calculation_type, a, b)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["a"], body["b"], body["type"]) == (a, b, calculation_type)
    assert body["result"] == pytest.approx(expected)
    (row,) = stored(db_session)
    assert (row.id, row.type) == (body["id"], calculation_type)
    assert row.result == pytest.approx(expected)


def test_add_normalizes_the_type(api_client):
    body = create(api_client, "divide", 10, 4).json()
    assert body["type"] == "Divide"
    assert body["result"] == pytest.approx(2.5)


def test_the_server_computes_the_result_and_the_client_cannot_set_the_owner(
    api_client, db_session
):
    response = api_client.post(
        "/calculations",
        json={"a": 2, "b": 3, "type": "Add", "result": 999, "user_id": 1},
    )
    assert response.status_code == 201
    assert response.json()["result"] == 5
    assert response.json()["user_id"] is None
    assert stored(db_session)[0].result == 5


def test_very_large_but_valid_numbers_are_accepted(api_client):
    response = create(api_client, "Add", 1e300, 1e300)
    assert response.status_code == 201
    assert response.json()["result"] == pytest.approx(2e300)


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_add_rejects_invalid_data(api_client, db_session, validation_status, body):
    response = api_client.post("/calculations", json=body)
    assert response.status_code == validation_status
    assert stored(db_session) == []


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_add_rejects_non_finite_numbers(api_client, db_session, validation_status, number):
    response = api_client.post(
        "/calculations",
        content=f'{{"a": {number}, "b": 1, "type": "Add"}}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == validation_status
    assert stored(db_session) == []


def test_add_rejects_a_result_that_is_too_large(api_client, db_session):
    response = create(api_client, "Multiply", 1e308, 10)
    assert response.status_code == 422
    assert "out of range" in response.text
    assert stored(db_session) == []


# ---- Read ------------------------------------------------------------------


def test_read_returns_the_calculation(api_client):
    created = create(api_client, "Multiply", 4, 5).json()
    response = api_client.get(f"/calculations/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_read_a_missing_calculation_returns_404(api_client):
    response = api_client.get("/calculations/999999")
    assert response.status_code == 404
    assert "not found" in response.text.lower()


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "1.5", "99999999999999"])
def test_read_rejects_invalid_ids(api_client, validation_status, bad_id):
    assert api_client.get(f"/calculations/{bad_id}").status_code == validation_status


# ---- Browse ----------------------------------------------------------------


def test_browse_an_empty_table_returns_an_empty_list(api_client):
    response = api_client.get("/calculations")
    assert response.status_code == 200
    assert response.json() == []


def test_browse_lists_calculations_in_id_order(api_client):
    created = [create(api_client, "Add", n, n).json() for n in (1, 2, 3)]
    assert api_client.get("/calculations").json() == created


def test_browse_pages_through_the_results(api_client):
    ids = [create(api_client, "Add", n, n).json()["id"] for n in range(1, 6)]
    middle = api_client.get("/calculations", params={"skip": 2, "limit": 2}).json()
    assert [item["id"] for item in middle] == ids[2:4]
    last = api_client.get("/calculations", params={"skip": 4}).json()
    assert [item["id"] for item in last] == ids[4:]
    assert api_client.get("/calculations", params={"skip": 10}).json() == []


@pytest.mark.parametrize(
    "params",
    [{"skip": -1}, {"limit": 0}, {"limit": 101}, {"skip": "abc"}, {"limit": "abc"}],
)
def test_browse_rejects_invalid_paging(api_client, validation_status, params):
    assert api_client.get("/calculations", params=params).status_code == validation_status


# ---- Edit ------------------------------------------------------------------


def test_edit_replaces_the_calculation_and_recomputes_the_result(api_client, db_session):
    created = create(api_client, "Add", 2, 3).json()
    response = api_client.put(
        f"/calculations/{created['id']}", json={"a": 10, "b": 4, "type": "Divide"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["created_at"] == created["created_at"]
    assert (body["a"], body["b"], body["type"]) == (10, 4, "Divide")
    assert body["result"] == pytest.approx(2.5)
    (row,) = stored(db_session)
    assert (row.a, row.b, row.type) == (10, 4, "Divide")
    assert row.result == pytest.approx(2.5)
    assert api_client.get(f"/calculations/{created['id']}").json() == body


def test_edit_normalizes_the_type(api_client):
    created = create(api_client).json()
    response = api_client.put(
        f"/calculations/{created['id']}", json={"a": 6, "b": 3, "type": "sub"}
    )
    assert response.json()["type"] == "Sub"
    assert response.json()["result"] == 3


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_edit_rejects_invalid_data_and_changes_nothing(
    api_client, db_session, validation_status, body
):
    created = create(api_client, "Add", 2, 3).json()
    before = snapshot(db_session)
    response = api_client.put(f"/calculations/{created['id']}", json=body)
    assert response.status_code == validation_status
    assert snapshot(db_session) == before


def test_edit_rejects_a_result_that_is_too_large(api_client, db_session):
    created = create(api_client, "Add", 2, 3).json()
    before = snapshot(db_session)
    response = api_client.put(
        f"/calculations/{created['id']}", json={"a": 1e308, "b": 10, "type": "Multiply"}
    )
    assert response.status_code == 422
    assert snapshot(db_session) == before


def test_edit_a_missing_calculation_returns_404(api_client, db_session):
    response = api_client.put("/calculations/999999", json={"a": 1, "b": 2, "type": "Add"})
    assert response.status_code == 404
    assert stored(db_session) == []


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "99999999999999"])
def test_edit_rejects_invalid_ids(api_client, validation_status, bad_id):
    response = api_client.put(f"/calculations/{bad_id}", json={"a": 1, "b": 2, "type": "Add"})
    assert response.status_code == validation_status


# ---- Delete ----------------------------------------------------------------


def test_delete_removes_the_calculation(api_client, db_session):
    created = create(api_client).json()
    response = api_client.delete(f"/calculations/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert api_client.get(f"/calculations/{created['id']}").status_code == 404
    assert stored(db_session) == []


def test_delete_leaves_other_calculations_alone(api_client, db_session):
    first = create(api_client, "Add", 1, 1).json()
    second = create(api_client, "Sub", 5, 2).json()
    api_client.delete(f"/calculations/{first['id']}")
    assert [row.id for row in stored(db_session)] == [second["id"]]


def test_delete_a_missing_calculation_returns_404(api_client):
    assert api_client.delete("/calculations/999999").status_code == 404


def test_deleting_twice_returns_404_the_second_time(api_client):
    created = create(api_client).json()
    assert api_client.delete(f"/calculations/{created['id']}").status_code == 204
    assert api_client.delete(f"/calculations/{created['id']}").status_code == 404


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "99999999999999"])
def test_delete_rejects_invalid_ids(api_client, validation_status, bad_id):
    assert api_client.delete(f"/calculations/{bad_id}").status_code == validation_status


# ---- The whole cycle, other methods, and owners -------------------------------


def test_full_create_read_update_delete_cycle(api_client, db_session):
    created = create(api_client, "Multiply", 6, 7)
    assert created.status_code == 201
    calculation_id = created.json()["id"]
    assert created.json()["result"] == 42

    assert api_client.get(f"/calculations/{calculation_id}").json()["result"] == 42

    updated = api_client.put(
        f"/calculations/{calculation_id}", json={"a": 6, "b": 7, "type": "Add"}
    )
    assert updated.json()["result"] == 13

    listing = api_client.get("/calculations").json()
    assert [(item["id"], item["type"], item["result"]) for item in listing] == [
        (calculation_id, "Add", 13)
    ]

    assert api_client.delete(f"/calculations/{calculation_id}").status_code == 204
    assert api_client.get(f"/calculations/{calculation_id}").status_code == 404
    assert api_client.get("/calculations").json() == []
    assert stored(db_session) == []


@pytest.mark.parametrize(
    "method, path",
    [("PATCH", "/calculations/1"), ("PUT", "/calculations"), ("DELETE", "/calculations")],
)
def test_unsupported_methods_return_405(api_client, method, path):
    assert api_client.request(method, path, json={}).status_code == 405


def make_owned_calculation(db_session):
    user = User(
        username="alice", email="alice@example.com", password_hash=hash_password("secret123")
    )
    db_session.add(user)
    db_session.commit()
    calculation = Calculation.create("Add", 1, 2, user_id=user.id)
    db_session.add(calculation)
    db_session.commit()
    return user.id, calculation.id


def test_calculations_with_an_owner_report_the_owner_id(api_client, db_session):
    user_id, calculation_id = make_owned_calculation(db_session)
    assert api_client.get(f"/calculations/{calculation_id}").json()["user_id"] == user_id


def test_deleting_a_calculation_leaves_its_user(api_client, db_session):
    user_id, calculation_id = make_owned_calculation(db_session)
    assert api_client.delete(f"/calculations/{calculation_id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(User, user_id) is not None