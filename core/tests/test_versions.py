"""Finalizing a draft into immutable MISMO XML versions (FR-02, FR-03).

Also: no taxpayer identifier or HMDA data in the XML (NFR-01, NFR-02), a
finalize audit entry per version (NFR-04), and a borrower reaches only their
own versions (NFR-08).

Needs the generated MISMO bindings and the staged DU schema (gitignored; see
mismo/README.md).
"""

import hashlib
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from helpers import COMPLETE, finalize
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core import services
from core.audit import verify_chain
from core.storage import AuditAction, AuditEvent, Borrower, Version
from mismo import SchemaValidationError, validate

MakeBorrower = Callable[[str], Borrower]
Login = Callable[[str], dict[str, str]]


@pytest.fixture
def alice(make_borrower: MakeBorrower, login: Login) -> tuple[Borrower, dict[str, str]]:
    return make_borrower("alice"), login("alice")


def stored_versions(db: Session, borrower: Borrower) -> list[Version]:
    db.expire_all()
    return list(
        db.scalars(
            select(Version)
            .where(Version.borrower_id == borrower.id)
            .order_by(Version.number)
        )
    )


def finalize_events(db: Session) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == AuditAction.Finalize)
            .order_by(AuditEvent.seq)
        )
    )


# Finalizing


def test_finalize_stores_valid_xml_with_its_hash(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    body = finalize(client, headers)

    [version] = stored_versions(db, borrower)
    assert set(body) == {"id", "number", "sha256", "createdAt"}
    assert body["id"] == version.id
    assert body["number"] == 1
    assert body["sha256"] == version.sha256 == hashlib.sha256(version.xml).hexdigest()
    validate(version.xml)  # FR-03: raises if not valid against the DU wrapper


def test_xml_has_no_taxpayer_identifier_or_hmda_data(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    finalize(client, headers)

    [version] = stored_versions(db, borrower)
    for marker in (b"TaxpayerIdentifier", b"SSN", b"HMDA"):
        assert marker not in version.xml


def test_finalize_leaves_the_draft_in_place(
    client: TestClient, alice: tuple[Borrower, dict[str, str]]
) -> None:
    _, headers = alice

    finalize(client, headers)

    draft = client.get("/draft", headers=headers).json()
    assert draft["borrower"]["firstName"] == "Alex"


def test_finalize_writes_one_audit_entry_bound_to_the_bytes(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    body = finalize(client, headers)

    [event] = finalize_events(db)
    assert event.borrower_id == borrower.id
    assert event.version_id == body["id"]
    assert event.detail == {"sha256": body["sha256"]}


def test_chain_verifies_after_several_finalizes(
    client: TestClient, db: Session, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    make_borrower("bob")
    alice, bob = login("alice"), login("bob")
    finalize(client, alice)
    finalize(client, bob)
    finalize(client, alice)

    check = verify_chain(db)

    assert check.ok
    assert check.entries == 3


# Immutability (FR-02)


def test_new_version_never_changes_an_earlier_one(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice
    first = finalize(client, headers)
    [original] = stored_versions(db, borrower)
    original_xml, original_sha256 = original.xml, original.sha256

    edited = {**COMPLETE, "borrower": {**COMPLETE["borrower"], "firstName": "Sam"}}
    second = finalize(client, headers, edited)

    v1, v2 = stored_versions(db, borrower)
    assert (first["number"], second["number"]) == (1, 2)
    assert v1.xml == original_xml
    assert v1.sha256 == original_sha256 == hashlib.sha256(v1.xml).hexdigest()
    assert v2.sha256 != v1.sha256
    assert b"Sam" in v2.xml and b"Sam" not in v1.xml


def test_finalizing_an_unchanged_draft_still_creates_a_version(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    finalize(client, headers)
    finalize(client, headers)

    v1, v2 = stored_versions(db, borrower)
    assert (v1.number, v2.number) == (1, 2)
    assert v1.sha256 == v2.sha256  # to_xml is deterministic


def test_version_numbers_are_per_borrower(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    make_borrower("bob")
    alice, bob = login("alice"), login("bob")

    finalize(client, alice)
    finalize(client, alice)
    bobs = finalize(client, bob)

    assert bobs["number"] == 1


@pytest.mark.parametrize(
    "sql",
    ["UPDATE version SET xml = 'tampered'", "DELETE FROM version"],
    ids=["update", "delete"],
)
def test_database_refuses_to_change_a_version(
    client: TestClient,
    db: Session,
    alice: tuple[Borrower, dict[str, str]],
    sql: str,
) -> None:
    _, headers = alice
    finalize(client, headers)

    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text(sql))


# Refusing to finalize


def test_finalize_without_a_draft_is_422(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    response = client.post("/draft/finalize", headers=headers)

    # No saved draft is validated as an empty one, so the body has the same
    # shape as any other incomplete draft.
    assert response.status_code == 422
    assert ["borrower"] in [error["loc"] for error in response.json()["detail"]]
    assert stored_versions(db, borrower) == []
    assert finalize_events(db) == []


@pytest.mark.parametrize(
    ("draft", "loc"),
    [
        (
            {**COMPLETE, "borrower": {"firstName": "Alex"}},
            ["borrower", "lastName"],
        ),
        (
            {
                **COMPLETE,
                "liabilities": [
                    {**COMPLETE["liabilities"][0], "liabilityType": "Installment"}
                ],
            },
            ["liabilities", 0],
        ),
    ],
    ids=["missing-field", "cross-field-rule"],
)
def test_incomplete_draft_is_422_with_the_field_and_nothing_stored(
    client: TestClient,
    db: Session,
    alice: tuple[Borrower, dict[str, str]],
    draft: dict[str, Any],
    loc: list[Any],
) -> None:
    borrower, headers = alice
    client.put("/draft", headers=headers, json=draft)

    response = client.post("/draft/finalize", headers=headers)

    assert response.status_code == 422
    assert loc in [error["loc"] for error in response.json()["detail"]]
    # Errors don't echo the borrower's values back.
    assert all("input" not in error for error in response.json()["detail"])
    assert stored_versions(db, borrower) == []
    assert finalize_events(db) == []


def test_schema_failure_stores_nothing(
    client: TestClient,
    db: Session,
    alice: tuple[Borrower, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A schema failure is a bug in core or mismo, not the borrower's input: it
    # surfaces as a server error and the whole transaction rolls back.
    borrower, headers = alice
    client.put("/draft", headers=headers, json=COMPLETE)

    def invalid(xml: bytes) -> None:
        raise SchemaValidationError(["line 1: simulated schema error"])

    monkeypatch.setattr(services, "validate", invalid)

    with pytest.raises(SchemaValidationError):
        client.post("/draft/finalize", headers=headers)

    assert stored_versions(db, borrower) == []
    assert finalize_events(db) == []


# Reading versions


def test_list_versions_in_order_without_xml(
    client: TestClient, alice: tuple[Borrower, dict[str, str]]
) -> None:
    _, headers = alice
    first = finalize(client, headers)
    second = finalize(client, headers)

    response = client.get("/versions", headers=headers)

    assert response.status_code == 200
    assert response.json() == [first, second]


def test_version_xml_is_the_exact_stored_bytes(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice
    body = finalize(client, headers)
    [version] = stored_versions(db, borrower)

    response = client.get(f"/versions/{body['id']}/xml", headers=headers)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml"
    assert response.content == version.xml
    assert response.headers["X-Content-SHA256"] == (
        hashlib.sha256(response.content).hexdigest()
    )


# Ownership and sessions (NFR-08)


def test_each_borrower_lists_only_their_own_versions(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    make_borrower("bob")
    alice, bob = login("alice"), login("bob")
    alices = finalize(client, alice)
    bobs = finalize(client, bob)

    assert client.get("/versions", headers=alice).json() == [alices]
    assert client.get("/versions", headers=bob).json() == [bobs]


def test_another_borrowers_version_looks_like_a_missing_one(
    client: TestClient, make_borrower: MakeBorrower, login: Login
) -> None:
    make_borrower("alice")
    make_borrower("bob")
    alice, bob = login("alice"), login("bob")
    alices = finalize(client, alice)

    theirs = client.get(f"/versions/{alices['id']}/xml", headers=bob)
    missing = client.get("/versions/999999/xml", headers=bob)

    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()


def test_non_numeric_version_id_is_422(
    client: TestClient, alice: tuple[Borrower, dict[str, str]]
) -> None:
    _, headers = alice

    assert client.get("/versions/abc/xml", headers=headers).status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", "/draft/finalize"), ("GET", "/versions"), ("GET", "/versions/1/xml")],
)
def test_version_routes_need_a_session(
    client: TestClient, method: str, path: str
) -> None:
    assert client.request(method, path).status_code == 401
