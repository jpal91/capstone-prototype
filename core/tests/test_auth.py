"""Borrower login, sessions, and logout (NFR-08)."""

from collections.abc import Callable
from datetime import timedelta
from hashlib import sha256

import pytest
from conftest import PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, update
from sqlalchemy.orm import Session

from core import auth
from core.storage import AuthSession, Borrower, Draft

MakeBorrower = Callable[[str], Borrower]
Login = Callable[[str], dict[str, str]]


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_all_makes_every_table(db: Session) -> None:
    tables = set(inspect(db.connection()).get_table_names())

    assert {"borrower", "draft", "session", "lender"} <= tables


# Login


def test_login_returns_a_token_and_stores_only_its_hash(
    client: TestClient, db: Session, make_borrower: MakeBorrower
) -> None:
    borrower = make_borrower("alice")

    response = client.post(
        "/auth/login", json={"username": "alice", "password": PASSWORD}
    )

    assert response.status_code == 200
    token = response.json()["token"]
    stored = db.scalars(
        select(AuthSession).where(AuthSession.borrower_id == borrower.id)
    ).one()
    assert stored.token_hash == sha256(token.encode()).digest()
    assert token.encode() != stored.token_hash


@pytest.mark.parametrize(
    ("username", "password"),
    [("alice", "wrong password"), ("nobody", PASSWORD)],
    ids=["wrong-password", "unknown-user"],
)
def test_failed_logins_look_the_same(
    client: TestClient, make_borrower: MakeBorrower, username: str, password: str
) -> None:
    make_borrower("alice")

    response = client.post(
        "/auth/login", json={"username": username, "password": password}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_unknown_user_still_checks_a_password_hash(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without a hash check, an unknown username would answer faster than a
    # wrong password and reveal which usernames exist.
    calls: list[str] = []
    real_verify = auth.HASHER.verify

    def spy(password: str, hash: str) -> bool:
        calls.append(hash)
        return real_verify(password, hash)

    monkeypatch.setattr(auth.HASHER, "verify", spy)

    client.post("/auth/login", json={"username": "nobody", "password": PASSWORD})

    assert calls == [auth.DUMMY_HASH]


def test_login_again_replaces_the_session(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    first = login("alice")
    second = login("alice")

    assert client.get("/draft", headers=first).status_code == 401
    assert client.get("/draft", headers=second).status_code == 200


# Sessions on borrower routes (NFR-08: no session -> 401)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-real-token"},
        {"Authorization": "Basic YWxpY2U6cGFzc3dvcmQ="},
        {"Authorization": "Bearer"},
    ],
    ids=["no-header", "unknown-token", "basic-scheme", "empty-bearer"],
)
def test_borrower_route_without_a_valid_session_is_401(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/draft", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_borrower_route_with_a_valid_session(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")

    response = client.get("/draft", headers=login("alice"))

    assert response.status_code == 200


def test_expired_session_is_401(
    client: TestClient, db: Session, make_borrower: MakeBorrower, login: Login
) -> None:
    borrower = make_borrower("alice")
    headers = login("alice")
    db.execute(
        update(AuthSession)
        .where(AuthSession.borrower_id == borrower.id)
        .values(expires_at=func.now() - timedelta(seconds=1))
    )

    assert client.get("/draft", headers=headers).status_code == 401


def test_borrower_sees_only_their_own_draft(
    client: TestClient, db: Session, make_borrower: MakeBorrower, login: Login
) -> None:
    alice = make_borrower("alice")
    make_borrower("bob")
    db.add(Draft(borrower_id=alice.id, data={"borrower": {"firstName": "Alice"}}))
    db.flush()

    alice_view = client.get("/draft", headers=login("alice"))
    bob_view = client.get("/draft", headers=login("bob"))

    assert alice_view.json() == {"borrower": {"firstName": "Alice"}}
    assert bob_view.json() is None


# Logout


def test_logout_ends_the_session(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    headers = login("alice")

    response = client.post("/auth/logout", headers=headers)

    assert response.status_code == 204
    assert client.get("/draft", headers=headers).status_code == 401


def test_logout_without_a_session_is_401(client: TestClient) -> None:
    assert client.post("/auth/logout").status_code == 401
