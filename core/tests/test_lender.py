"""The lender API: a lender fetches an application only with its own, active
grant (FR-07), authenticating with its own credentials (NFR-03).

Also: grants and revokes take effect end to end (FR-05, FR-06), every fetch and
denied fetch is audited with the real reason (NFR-04), every denial looks the
same from outside, including a grant that doesn't exist, and the borrower sees
when each grant was last fetched (FR-08).
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from helpers import finalize, lender_auth
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.audit import verify_chain
from core.storage import AuditAction, AuditEvent, Borrower, Grant, Lender, Version

MakeBorrower = Callable[[str], Borrower]
MakeLender = Callable[[str], Lender]
Login = Callable[[str], dict[str, str]]

MISSING = 999_999


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


def grant(client: TestClient, s: Setup, lender: Lender) -> int:
    response = client.post(
        "/grants",
        headers=s.headers,
        json={
            "lenderId": lender.id,
            "versionId": s.version_id,
            "expiresAt": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def revoke(client: TestClient, s: Setup, grant_id: int) -> None:
    response = client.post(f"/grants/{grant_id}/revoke", headers=s.headers)
    assert response.status_code == 200, response.text


def expired_grant(db: Session, s: Setup, lender: Lender) -> int:
    # The API refuses a past expiry, and now() is frozen for the test.
    row = Grant(
        borrower_id=s.borrower.id,
        lender_id=lender.id,
        version_id=s.version_id,
        expires_at=func.now() - timedelta(seconds=1),
    )
    db.add(row)
    db.flush()
    return row.id


def fetch(client: TestClient, lender: Lender, grant_id: int) -> httpx.Response:
    return client.get(
        f"/lender/grants/{grant_id}/application", auth=lender_auth(lender)
    )


def events(db: Session, *actions: AuditAction) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.action.in_(actions))
            .order_by(AuditEvent.seq)
        )
    )


def fetch_events(db: Session) -> list[AuditEvent]:
    return events(db, AuditAction.Fetch, AuditAction.FetchDenied)


def stored_xml(db: Session, version_id: int) -> bytes:
    return db.scalars(select(Version.xml).where(Version.id == version_id)).one()


# Fetching (FR-07)


def test_own_active_grant_returns_the_exact_version_bytes(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant_id = grant(client, setup, setup.a)

    response = fetch(client, setup.a, grant_id)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml"
    assert response.content == stored_xml(db, setup.version_id)
    assert response.headers["X-Content-SHA256"] == (
        hashlib.sha256(response.content).hexdigest()
    )


def test_fetch_writes_one_audit_entry_with_every_id(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant_id = grant(client, setup, setup.a)

    response = fetch(client, setup.a, grant_id)

    [event] = fetch_events(db)
    assert event.action == AuditAction.Fetch
    assert event.borrower_id == setup.borrower.id
    assert event.lender_id == setup.a.id
    assert event.version_id == setup.version_id
    assert event.grant_id == grant_id
    assert event.detail == {"sha256": response.headers["X-Content-SHA256"]}


def test_each_fetch_is_audited(client: TestClient, db: Session, setup: Setup) -> None:
    grant_id = grant(client, setup, setup.a)

    fetch(client, setup.a, grant_id)
    fetch(client, setup.a, grant_id)

    assert [e.action for e in fetch_events(db)] == [AuditAction.Fetch] * 2


# Denials: the consent matrix. Every denial is the same 404 as an unknown path,
# and its audit entry records the actual reason.


def own_revoked(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    grant_id = grant(client, s, s.a)
    revoke(client, s, grant_id)
    return s.a, grant_id


def own_expired(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    return s.a, expired_grant(db, s, s.a)


def other_active(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    return s.b, grant(client, s, s.a)


def other_revoked(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    _, grant_id = own_revoked(client, db, s)
    return s.b, grant_id


def other_expired(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    return s.b, expired_grant(db, s, s.a)


def missing(client: TestClient, db: Session, s: Setup) -> tuple[Lender, int]:
    return s.a, MISSING


DENIALS = [
    (own_revoked, "revoked"),
    (own_expired, "expired"),
    # Another lender's grant is reported as such whatever its state, so the log
    # never records that lender learning anything about it.
    (other_active, "other_lender"),
    (other_revoked, "other_lender"),
    (other_expired, "other_lender"),
    (missing, "not_found"),
]
DENIAL_IDS = [arrange.__name__ for arrange, _ in DENIALS]


def unknown_path(client: TestClient, lender: Lender) -> httpx.Response:
    return client.get("/lender/no-such-route", auth=lender_auth(lender))


@pytest.mark.parametrize(("arrange", "reason"), DENIALS, ids=DENIAL_IDS)
def test_denial_is_indistinguishable_from_an_unknown_path(
    client: TestClient,
    db: Session,
    setup: Setup,
    arrange: Callable[..., tuple[Lender, int]],
    reason: str,
) -> None:
    lender, grant_id = arrange(client, db, setup)

    denied = fetch(client, lender, grant_id)
    unknown = unknown_path(client, lender)

    assert denied.status_code == unknown.status_code == 404
    assert denied.content == unknown.content
    assert dict(denied.headers) == dict(unknown.headers)


@pytest.mark.parametrize(("arrange", "reason"), DENIALS, ids=DENIAL_IDS)
def test_denial_is_audited_with_the_actual_reason(
    client: TestClient,
    db: Session,
    setup: Setup,
    arrange: Callable[..., tuple[Lender, int]],
    reason: str,
) -> None:
    # Also checks the denial is committed: the harness rolls back a request
    # that raises, so a raised 404 would leave no entry here.
    lender, grant_id = arrange(client, db, setup)

    fetch(client, lender, grant_id)

    [event] = fetch_events(db)
    assert event.action == AuditAction.FetchDenied
    assert event.detail == {"reason": reason}
    assert event.lender_id == lender.id  # the caller, not the grant's lender
    assert event.grant_id == grant_id


def test_denial_of_an_existing_grant_records_its_borrower_and_version(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant_id = grant(client, setup, setup.a)

    fetch(client, setup.b, grant_id)

    [event] = fetch_events(db)
    assert event.borrower_id == setup.borrower.id
    assert event.version_id == setup.version_id


def test_denial_of_a_missing_grant_records_no_borrower_or_version(
    client: TestClient, db: Session, setup: Setup
) -> None:
    fetch(client, setup.a, MISSING)

    [event] = fetch_events(db)
    assert event.borrower_id is None
    assert event.version_id is None


def test_non_numeric_grant_id_is_422_and_not_audited(
    client: TestClient, db: Session, setup: Setup
) -> None:
    response = client.get("/lender/grants/abc/application", auth=lender_auth(setup.a))

    assert response.status_code == 422
    assert fetch_events(db) == []


# Grants and revokes end to end (FR-05, FR-06)


def test_only_granted_lenders_can_fetch(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)
    b = grant(client, setup, setup.b)

    assert fetch(client, setup.a, a).status_code == 200
    assert fetch(client, setup.b, b).status_code == 200
    # C has no grant: it can't use either of the others'.
    assert fetch(client, setup.c, a).status_code == 404
    assert fetch(client, setup.c, b).status_code == 404


def test_revoking_one_grant_leaves_the_others_working(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)
    b = grant(client, setup, setup.b)
    assert fetch(client, setup.a, a).status_code == 200

    revoke(client, setup, a)

    assert fetch(client, setup.a, a).status_code == 404
    assert fetch(client, setup.b, b).status_code == 200


def test_a_lenders_other_grant_survives_revoking_one(
    client: TestClient, db: Session, setup: Setup
) -> None:
    first = grant(client, setup, setup.a)
    second = grant(client, setup, setup.a)

    revoke(client, setup, first)

    assert fetch(client, setup.a, first).status_code == 404
    assert fetch(client, setup.a, second).status_code == 200


# Lender credentials (NFR-03)


def bad_credentials(setup: Setup) -> dict[str, dict[str, Any]]:
    client_id, secret = lender_auth(setup.a)
    return {
        "wrong-secret": {"auth": (client_id, "wrong")},
        "other-lenders-secret": {"auth": (client_id, lender_auth(setup.b)[1])},
        "unknown-client": {"auth": ("nobody", secret)},
        "empty": {"auth": ("", "")},
        "no-header": {},
        "malformed-basic": {"headers": {"Authorization": "Basic !!!"}},
        "borrower-token": {"headers": setup.headers},
    }


BAD_CREDENTIALS = [
    "wrong-secret",
    "other-lenders-secret",
    "unknown-client",
    "empty",
    "no-header",
    "malformed-basic",
    "borrower-token",
]


@pytest.mark.parametrize("path", ["/lender/grants", "/lender/grants/{}/application"])
@pytest.mark.parametrize("case", BAD_CREDENTIALS)
def test_bad_credentials_are_401_and_not_audited(
    client: TestClient, db: Session, setup: Setup, case: str, path: str
) -> None:
    grant_id = grant(client, setup, setup.a)

    response = client.get(path.format(grant_id), **bad_credentials(setup)[case])

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Basic"
    assert fetch_events(db) == []


def test_unknown_client_and_wrong_secret_look_the_same(
    client: TestClient, setup: Setup
) -> None:
    client_id, secret = lender_auth(setup.a)

    unknown = client.get("/lender/grants", auth=("nobody", secret))
    wrong = client.get("/lender/grants", auth=(client_id, "wrong"))

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.content == wrong.content
    assert dict(unknown.headers) == dict(wrong.headers)


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/draft"), ("GET", "/versions"), ("GET", "/grants")],
)
def test_lender_credentials_dont_open_borrower_routes(
    client: TestClient, setup: Setup, method: str, path: str
) -> None:
    response = client.request(method, path, auth=lender_auth(setup.a))

    assert response.status_code == 401


# Listing a lender's grants


def test_lender_lists_only_its_own_active_grants(
    client: TestClient, db: Session, setup: Setup
) -> None:
    active = grant(client, setup, setup.a)
    revoked = grant(client, setup, setup.a)
    revoke(client, setup, revoked)
    expired_grant(db, setup, setup.a)
    grant(client, setup, setup.b)

    response = client.get("/lender/grants", auth=lender_auth(setup.a))

    assert response.status_code == 200
    assert [g["grantId"] for g in response.json()] == [active]


def test_lender_grant_list_has_no_application_data(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant_id = grant(client, setup, setup.a)
    sha256 = db.scalars(
        select(Version.sha256).where(Version.id == setup.version_id)
    ).one()

    [item] = client.get("/lender/grants", auth=lender_auth(setup.a)).json()

    assert set(item) == {"grantId", "expiresAt", "sha256"}
    assert item["grantId"] == grant_id
    assert item["sha256"] == sha256


def test_lender_grant_list_is_in_grant_order(client: TestClient, setup: Setup) -> None:
    ids = [grant(client, setup, setup.a) for _ in range(3)]

    listed = client.get("/lender/grants", auth=lender_auth(setup.a)).json()

    assert [g["grantId"] for g in listed] == ids


def test_listing_grants_is_not_audited(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant(client, setup, setup.a)

    client.get("/lender/grants", auth=lender_auth(setup.a))

    assert fetch_events(db) == []


def test_lender_with_no_grants_gets_an_empty_list(
    client: TestClient, setup: Setup
) -> None:
    grant(client, setup, setup.a)

    response = client.get("/lender/grants", auth=lender_auth(setup.c))

    assert response.status_code == 200
    assert response.json() == []


# The audit chain (NFR-04)


def test_chain_verifies_after_fetches_and_denials(
    client: TestClient, db: Session, setup: Setup
) -> None:
    a = grant(client, setup, setup.a)
    fetch(client, setup.a, a)
    fetch(client, setup.b, a)
    revoke(client, setup, a)
    fetch(client, setup.a, a)
    fetch(client, setup.a, MISSING)

    check = verify_chain(db)

    assert check.ok
    # finalize, grant, fetch, denied, revoke, denied, denied
    assert check.entries == 7
    assert [e.action for e in fetch_events(db)] == [
        AuditAction.Fetch,
        AuditAction.FetchDenied,
        AuditAction.FetchDenied,
        AuditAction.FetchDenied,
    ]


# When each lender last fetched (FR-08), read from the audit log.
# now() is frozen per test, so every fetch in a test has the same `at`: these
# tests can't tell "newest fetch" from "any fetch", only fetched from not.


def last_fetched(client: TestClient, s: Setup) -> dict[int, str | None]:
    grants = client.get("/grants", headers=s.headers).json()
    return {g["id"]: g["lastFetchedAt"] for g in grants}


def fetched_at(db: Session) -> datetime:
    [event] = events(db, AuditAction.Fetch)
    return event.at


def test_new_grant_has_not_been_fetched(client: TestClient, setup: Setup) -> None:
    response = client.post(
        "/grants",
        headers=setup.headers,
        json={
            "lenderId": setup.a.id,
            "versionId": setup.version_id,
            "expiresAt": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        },
    )

    assert response.json()["lastFetchedAt"] is None
    assert last_fetched(client, setup) == {response.json()["id"]: None}


def test_fetch_sets_last_fetched_at_from_the_audit_entry(
    client: TestClient, db: Session, setup: Setup
) -> None:
    grant_id = grant(client, setup, setup.a)

    fetch(client, setup.a, grant_id)

    listed = datetime.fromisoformat(last_fetched(client, setup)[grant_id] or "")
    assert listed == fetched_at(db)


@pytest.mark.parametrize(("arrange", "reason"), DENIALS[:-1], ids=DENIAL_IDS[:-1])
def test_denied_fetches_dont_count(
    client: TestClient,
    db: Session,
    setup: Setup,
    arrange: Callable[..., tuple[Lender, int]],
    reason: str,
) -> None:
    lender, grant_id = arrange(client, db, setup)

    assert fetch(client, lender, grant_id).status_code == 404

    assert last_fetched(client, setup)[grant_id] is None


def test_last_fetched_at_is_per_grant(client: TestClient, setup: Setup) -> None:
    a = grant(client, setup, setup.a)
    b = grant(client, setup, setup.b)
    a_again = grant(client, setup, setup.a)

    fetch(client, setup.a, a)

    listed = last_fetched(client, setup)
    assert listed[a] is not None
    assert listed[b] is None
    assert listed[a_again] is None  # same lender, different grant


def test_l01_revoked_grant_still_shows_its_earlier_fetch(
    client: TestClient, db: Session, setup: Setup
) -> None:
    # Revoking stops future fetches; the copy already fetched stays with the
    # lender, and the borrower can see that it was fetched.
    grant_id = grant(client, setup, setup.a)
    fetch(client, setup.a, grant_id)

    response = client.post(f"/grants/{grant_id}/revoke", headers=setup.headers)
    fetch(client, setup.a, grant_id)  # denied, and doesn't count

    revoked = response.json()
    assert revoked["status"] == "revoked"
    assert datetime.fromisoformat(revoked["lastFetchedAt"]) == fetched_at(db)
    assert last_fetched(client, setup)[grant_id] == revoked["lastFetchedAt"]
