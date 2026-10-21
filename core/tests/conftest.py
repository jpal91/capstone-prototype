"""Test harness for `core`: a real Postgres, nothing left behind.

Each test runs inside one outer transaction on the database in `DATABASE_URL`
(the compose `db` by default; start it with `just db-up`). The tables are
dropped and recreated inside that transaction, so a stale dev schema doesn't
matter, and the transaction is rolled back at the end, so the dev database is
unchanged. Postgres DDL is transactional, which is what makes this work.

Route sessions and the test's own `db` session share the connection through
savepoints: a route's commit releases a savepoint, and a route's rollback
undoes only that request, as `get_session` does in production.

If the database isn't reachable, every test that needs it is skipped.

Because each test is one transaction, Postgres's `now()` stays at the test's
start time throughout. To make something "expired", set it relative to
`func.now()`, not to a Python clock.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.app import app
from core.auth import HASHER
from core.db import engine, get_session
from core.storage import Base, Borrower, Lender

PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="session")
def _database_up() -> None:
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Postgres is not running (start it with `just db-up`)")


@pytest.fixture
def connection(_database_up: None) -> Iterator[Connection]:
    with engine.connect() as conn:
        outer = conn.begin()
        Base.metadata.drop_all(conn)
        Base.metadata.create_all(conn)
        yield conn
        outer.rollback()


def _savepoint_session(conn: Connection) -> Session:
    return Session(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
def db(connection: Connection) -> Iterator[Session]:
    """A session for arranging and inspecting data directly."""
    with _savepoint_session(connection) as session:
        yield session


@pytest.fixture
def client(connection: Connection) -> Iterator[TestClient]:
    """An HTTP client for the app, with every request on the test's transaction.

    Not entered as a context manager, so the lifespan (`create_all` on the real
    engine) doesn't run.
    """

    def test_session() -> Iterator[Session]:
        with _savepoint_session(connection) as session, session.begin():
            yield session

    app.dependency_overrides[get_session] = test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_borrower(db: Session) -> Callable[[str], Borrower]:
    """Create a borrower whose password is `PASSWORD`."""

    def make(username: str) -> Borrower:
        borrower = Borrower(username=username, password_hash=HASHER.hash(PASSWORD))
        db.add(borrower)
        db.flush()
        return borrower

    return make


@pytest.fixture
def make_lender(db: Session) -> Callable[[str], Lender]:
    """Create a lender. Its credentials are placeholders until the lender API."""

    def make(name: str) -> Lender:
        lender = Lender(name=name, client_id=name.lower(), hashed_secret=b"unused")
        db.add(lender)
        db.flush()
        return lender

    return make


@pytest.fixture
def login(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Log in and return the Authorization header for the new session."""

    def do_login(username: str) -> dict[str, str]:
        response = client.post(
            "/auth/login", json={"username": username, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return do_login
