"""Grants: a borrower shares one version with one lender until an expiry (FR-05),
and can revoke each grant independently (FR-06).

Also: a grant or revoke event per change (NFR-04), the database refusing any
change but a single revoke, and a borrower reaching only their own grants
(NFR-08).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from helpers import finalize
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.audit import verify_chain
from core.storage import AuditAction, AuditEvent, Borrower, Grant, Lender

MakeBorrower = Callable[[str], Borrower]
MakeLender = Callable[[str], Lender]
Login = Callable[[str], dict[str, str]]


@dataclass
class Setup:
    """Alice with one finalized version, and three lenders."""

    borrower: Borrower
    headers: dict[str, str]
    version_id: int
    a: Lender
    b: Lender
    c: Lender


@pytest.fixture
def setup(
    client: TestClient,
    make_borrower: MakeBorrower,
    make_lender: MakeLender,
    login: Login,
) -> Setup:
    borrower = make_borrower("alice")
    headers = login("alice")
    version = finalize(client, headers)
    return Setup(
        borrower,
        headers,
        version["id"],
        make_lender("Lender A"),
        make_lender("Lender B"),
        make_lender("Lender C"),
    )


def in_days(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def grant(
    client: TestClient, s: Setup, lender: Lender, expires_at: str | None = None
) -> dict[str, Any]:
    response = client.post(
        "/grants",
        headers=s.headers,
        json={
            "lenderId": lender.id,
            "versionId": s.version_id,
            "expiresAt": expires_at or in_days(7),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def statuses(client: TestClient, headers: dict[str, str]) -> dict[str, str]:
    return {
        g["lenderName"]: g["status"]
        for g in client.get("/grants", headers=headers).json()
    }


def events(db: Session, action: AuditAction) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == action)
            .order_by(AuditEvent.seq)
        )
    )


def grant_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Grant)) or 0


def insert_grant(db: Session, s: Setup, lender: Lender, expires_at: Any) -> Grant:
    """Insert directly, for expiries the API refuses (already past, or now)."""
    row = Grant(
        borrower_id=s.borrower.id,
        lender_id=lender.id,
        version_id=s.version_id,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return row


# Lenders


def test_lenders_lists_names_only_in_order(client: TestClient, setup: Setup) -> None:
    response = client.get("/lenders", headers=setup.headers)

    assert response.status_code == 200
    assert response.json() == [
        {"id": setup.a.id, "name": "Lender A"},
        {"id": setup.b.id, "name": "Lender B"},
        {"id": setup.c.id, "name": "Lender C"},
    ]


# Creating a grant (FR-05)


def test_grant_is_bound_to_lender_version_and_expiry(
    client: TestClient, setup: Setup
) -> None:
    expires_at = in_days(30)

    body = grant(client, setup, setup.a, expires_at)

    assert body["status"] == "active"
    assert (body["lenderId"], body["lenderName"]) == (setup.a.id, "Lender A")
    assert (body["versionId"], body["versionNumber"]) == (setup.version_id, 1)
    assert datetime.fromisoformat(body["expiresAt"]) == datetime.fromisoformat(
        expires_at
    )
    assert body["revokedAt"] is None


def test_grant_writes_one_audit_entry_with_every_id(
    client: TestClient, db: Session, setup: Setup
) -> None:
    # Expiry given with a non-UTC offset; the audit entry records it in UTC.
    local = (datetime.now(UTC) + timedelta(days=7)).astimezone(
        timezone(timedelta(hours=-7))
    )

    body = grant(client, setup, setup.a, local.isoformat())

    [event] = events(db, AuditAction.Grant)
    assert (event.borrower_id, event.lender_id, event.version_id, event.grant_id) == (
        setup.borrower.id,
        setup.a.id,
        setup.version_id,
        body["id"],
    )
    assert event.detail == {"expiresAt": local.astimezone(UTC).isoformat()}


def test_grants_to_a_and_b_but_not_c(client: TestClient, setup: Setup) -> None:
    # FR-05's setup; step 7 checks that C's fetch is denied.
    grant(client, setup, setup.a)
    grant(client, setup, setup.b)

    assert statuses(client, setup.headers) == {
        "Lender A": "active",
        "Lender B": "active",
    }


def test_same_lender_can_hold_more_than_one_grant(
    client: TestClient, setup: Setup
) -> None:
    first = grant(client, setup, setup.a)
    second = grant(client, setup, setup.a)

    listed = client.get("/grants", headers=setup.headers).json()
    assert [g["id"] for g in listed] == [first["id"], second["id"]]


def test_grants_are_listed_in_creation_order(client: TestClient, setup: Setup) -> None:
    created = [grant(client, setup, lender) for lender in (setup.c, setup.a, setup.b)]

    listed = client.get("/grants", headers=setup.headers).json()

    assert listed == created


@pytest.mark.parametrize(
    ("change", "status"),
    [
        ({"versionId": 999999}, 404),
        ({"lenderId": 999999}, 404),
        ({"expiresAt": "2020-01-01T00:00:00Z"}, 422),
        ({"expiresAt": "2099-01-01T00:00:00"}, 422),
        ({"expiresAt": None}, 422),
    ],
    ids=[
        "unknown-version",
        "unknown-lender",
        "expiry-in-past",
        "expiry-without-timezone",
        "missing-expiry",
    ],
)
def test_refused_grant_creates_nothing(
    client: TestClient,
    db: Session,
    setup: Setup,
    change: dict[str, Any],
    status: int,
) -> None:
    body = {"lenderId": setup.a.id, "versionId": setup.version_id}
    body["expiresAt"] = in_days(7)
    body.update(change)
    body = {k: v for k, v in body.items() if v is not None}

    response = client.post("/grants", headers=setup.headers, json=body)

    assert response.status_code == status
    assert grant_count(db) == 0
    assert events(db, AuditAction.Grant) == []


def test_cannot_grant_another_borrowers_version(
    client: TestClient,
    db: Session,
    setup: Setup,
    make_borrower: MakeBorrower,
    login: Login,
) -> None:
    make_borrower("bob")
    bob = login("bob")

    response = client.post(
        "/grants",
        headers=bob,
        json={
            "lenderId": setup.a.id,
            "versionId": setup.version_id,
            "expiresAt": in_days(7),
        },
    )

    assert response.status_code == 404
    assert grant_count(db) == 0


# Status


def test_grant_past_its_expiry_is_expired(
    client: TestClient, db: Session, setup: Setup
) -> None:
    # now() is frozen for the test (see conftest), so expiry is set against it.
    insert_grant(db, setup, setup.a, func.now() - timedelta(seconds=1))
    grant(client, setup, setup.b)

    assert statuses(client, setup.headers) == {
        "Lender A": "expired",
        "Lender B": "active",
    }


def test_grant_expiring_exactly_now_is_expired(
    client: TestClient, db: Session, setup: Setup
) -> None:
    insert_grant(db, setup, setup.a, func.now())

    assert statuses(client, setup.headers) == {"Lender A": "expired"}


# Revoking (FR-06)


def test_revoking_a_leaves_b_active(client: TestClient, setup: Setup) -> None:
    a = grant(client, setup, setup.a)
    grant(client, setup, setup.b)

    response = client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    assert response.json()["revokedAt"] is not None
    assert statuses(client, setup.headers) == {
        "Lender A": "revoked",
        "Lender B": "active",
    }


def test_revoke_writes_one_audit_entry_with_every_id(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)

    client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    [event] = events(db, AuditAction.Revoke)
    assert (event.borrower_id, event.lender_id, event.version_id, event.grant_id) == (
        setup.borrower.id,
        setup.a.id,
        setup.version_id,
        a["id"],
    )


def test_revoking_twice_is_one_revoke(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)
    first = client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    second = client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(events(db, AuditAction.Revoke)) == 1


def test_an_expired_grant_can_still_be_revoked(
    client: TestClient, db: Session, setup: Setup
) -> None:
    expired = insert_grant(db, setup, setup.a, func.now() - timedelta(seconds=1))

    response = client.post(f"/grants/{expired.id}/revoke", headers=setup.headers)

    assert response.json()["status"] == "revoked"
    assert len(events(db, AuditAction.Revoke)) == 1


def test_chain_verifies_after_finalize_grant_and_revoke(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)
    grant(client, setup, setup.b)
    client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    check = verify_chain(db)

    assert check.ok
    assert check.entries == 4  # finalize, grant, grant, revoke


# The database allows exactly one change: revoking an unrevoked grant.


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE access_grant SET lender_id = :other_lender",
        "UPDATE access_grant SET expires_at = expires_at + interval '1 day'",
        "UPDATE access_grant SET created_at = created_at - interval '1 day'",
        "DELETE FROM access_grant",
        "TRUNCATE access_grant",
    ],
    ids=["change-lender", "extend-expiry", "backdate", "delete", "truncate"],
)
def test_database_refuses_to_change_a_grant(
    client: TestClient, db: Session, setup: Setup, sql: str
) -> None:
    grant(client, setup, setup.a)
    params = {"other_lender": setup.b.id} if ":other_lender" in sql else {}

    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text(sql), params)


def test_database_refuses_to_change_a_grants_version(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant(client, setup, setup.a)
    newer = finalize(client, setup.headers)

    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text("UPDATE access_grant SET version_id = :v"), {"v": newer["id"]})


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE access_grant SET revoked_at = NULL",
        "UPDATE access_grant SET revoked_at = revoked_at + interval '1 second'",
    ],
    ids=["un-revoke", "re-date-revoke"],
)
def test_database_refuses_to_change_a_revoke(
    client: TestClient, db: Session, setup: Setup, sql: str
) -> None:
    a = grant(client, setup, setup.a)
    client.post(f"/grants/{a['id']}/revoke", headers=setup.headers)

    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text(sql))


def test_database_allows_revoking(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant(client, setup, setup.a)

    db.execute(text("UPDATE access_grant SET revoked_at = now()"))

    assert statuses(client, setup.headers) == {"Lender A": "revoked"}


# Ownership and sessions (NFR-08)


def test_each_borrower_lists_only_their_own_grants(
    client: TestClient, setup: Setup, make_borrower: MakeBorrower, login: Login
) -> None:
    grant(client, setup, setup.a)
    make_borrower("bob")
    bob = login("bob")

    assert client.get("/grants", headers=bob).json() == []


def test_another_borrowers_grant_cannot_be_revoked(
    client: TestClient,
    db: Session,
    setup: Setup,
    make_borrower: MakeBorrower,
    login: Login,
) -> None:
    a = grant(client, setup, setup.a)
    make_borrower("bob")
    bob = login("bob")

    theirs = client.post(f"/grants/{a['id']}/revoke", headers=bob)
    missing = client.post("/grants/999999/revoke", headers=bob)

    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()
    assert statuses(client, setup.headers) == {"Lender A": "active"}
    assert events(db, AuditAction.Revoke) == []


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/lenders"),
        ("GET", "/grants"),
        ("POST", "/grants"),
        ("POST", "/grants/1/revoke"),
    ],
)
def test_grant_routes_need_a_session(
    client: TestClient, method: str, path: str
) -> None:
    assert client.request(method, path).status_code == 401
