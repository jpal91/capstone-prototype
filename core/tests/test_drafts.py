"""Borrower drafts: save and resume the supported URLA subset (FR-01).

Also covers what a draft refuses to hold (NFR-01, NFR-02) and that a borrower
reaches only their own draft (NFR-08).
"""

from collections.abc import Callable
from datetime import timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from core.storage import Borrower, Draft
from mismo import UrlaDraft

MakeBorrower = Callable[[str], Borrower]
Login = Callable[[str], dict[str, str]]

EMPTY = {
    "borrower": {},
    "address": {},
    "subjectProperty": {},
    "income": {},
    "assets": [],
    "liabilities": [],
    "loan": {},
}

# A partly filled draft, as the portal would save it mid-form. Synthetic (NFR-06).
PARTIAL = {
    **EMPTY,
    "borrower": {"firstName": "Alex", "lastName": "Example"},
    "income": {"employerName": "Example Corp", "monthlyIncome": "6000.00"},
    "assets": [
        {
            "institutionName": "Example Bank",
            "assetType": "Checking",
            "amount": "1000.00",
        }
    ],
}


def saved(response: Response) -> dict[str, Any]:
    """The draft in a response, in the form `core` stores it (unset fields omitted)."""
    return UrlaDraft.model_validate(response.json()).model_dump(
        mode="json", by_alias=True, exclude_none=True
    )


def stored_draft(db: Session, borrower: Borrower) -> Draft | None:
    db.expire_all()
    return db.scalars(select(Draft).where(Draft.borrower_id == borrower.id)).first()


@pytest.fixture
def alice(make_borrower: MakeBorrower, login: Login) -> tuple[Borrower, dict[str, str]]:
    return make_borrower("alice"), login("alice")


# GET before anything is saved


def test_get_before_saving_returns_an_empty_draft(
    client: TestClient, alice: tuple[Borrower, dict[str, str]]
) -> None:
    _, headers = alice

    response = client.get("/draft", headers=headers)

    assert response.status_code == 200
    assert saved(response) == EMPTY
    assert "Last-Modified" not in response.headers


# Save and resume


def test_put_then_get_returns_what_was_saved(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    put = client.put("/draft", headers=headers, json=PARTIAL)
    response = client.get("/draft", headers=headers)

    assert put.status_code == 204
    assert response.status_code == 200
    assert saved(response) == PARTIAL
    row = stored_draft(db, borrower)
    assert row is not None
    assert parsedate_to_datetime(
        response.headers["Last-Modified"]
    ) == row.updated_at.replace(microsecond=0)


def test_stored_json_is_camel_case_with_exact_money_strings(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice

    client.put("/draft", headers=headers, json=PARTIAL)

    row = stored_draft(db, borrower)
    assert row is not None
    assert row.data == PARTIAL
    assert row.data["income"]["monthlyIncome"] == "6000.00"


def test_put_replaces_the_whole_draft(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    borrower, headers = alice
    client.put("/draft", headers=headers, json=PARTIAL)
    replacement = {**EMPTY, "loan": {"loanPurpose": "Refinance"}}

    client.put("/draft", headers=headers, json=replacement)

    assert saved(client.get("/draft", headers=headers)) == replacement
    rows = db.scalars(select(Draft).where(Draft.borrower_id == borrower.id)).all()
    assert len(rows) == 1


def test_put_moves_updated_at(
    client: TestClient, db: Session, alice: tuple[Borrower, dict[str, str]]
) -> None:
    # now() is frozen for the whole test (see conftest), so back-date the row
    # and check that the next save brings it forward again.
    borrower, headers = alice
    client.put("/draft", headers=headers, json=PARTIAL)
    db.execute(
        update(Draft)
        .where(Draft.borrower_id == borrower.id)
        .values(updated_at=func.now() - timedelta(days=1))
    )

    client.put("/draft", headers=headers, json=PARTIAL)

    row = stored_draft(db, borrower)
    assert row is not None
    assert row.updated_at == db.scalar(select(func.now()))


# What a draft refuses to hold


@pytest.mark.parametrize(
    "body",
    [
        {"borrower": {"ssn": "000-00-0000"}},
        {"borrower": {"taxpayerIdentifier": "000000000"}},
        {"hmda": {"ethnicity": "NotProvided"}},
        {"borrower": {"nickname": "Al"}},
        {"income": {"monthlyIncome": "-1.00"}},
        {"income": {"monthlyIncome": "1.005"}},
        {"loan": {"loanTermMonths": "thirty years"}},
        {"loan": {"loanPurpose": "Lease"}},
    ],
    ids=[
        "ssn-NFR-01",
        "taxpayer-id-NFR-01",
        "hmda-NFR-02",
        "unknown-field",
        "negative-amount",
        "fractional-cents",
        "wrong-type",
        "unknown-enum",
    ],
)
def test_invalid_draft_is_422_and_nothing_is_stored(
    client: TestClient,
    db: Session,
    alice: tuple[Borrower, dict[str, str]],
    body: dict[str, Any],
) -> None:
    borrower, headers = alice
    client.put("/draft", headers=headers, json=PARTIAL)

    response = client.put("/draft", headers=headers, json=body)

    assert response.status_code == 422
    row = stored_draft(db, borrower)
    assert row is not None
    assert row.data == PARTIAL


# Ownership (NFR-08)


def test_each_borrower_reads_and_writes_only_their_own_draft(
    client: TestClient, db: Session, make_borrower: MakeBorrower, login: Login
) -> None:
    alice, bob = make_borrower("alice"), make_borrower("bob")
    alice_headers, bob_headers = login("alice"), login("bob")
    bobs = {**EMPTY, "borrower": {"firstName": "Bob"}}

    client.put("/draft", headers=alice_headers, json=PARTIAL)
    client.put("/draft", headers=bob_headers, json=bobs)

    assert saved(client.get("/draft", headers=alice_headers)) == PARTIAL
    assert saved(client.get("/draft", headers=bob_headers)) == bobs
    alice_row, bob_row = stored_draft(db, alice), stored_draft(db, bob)
    assert alice_row is not None and alice_row.data == PARTIAL
    assert bob_row is not None and bob_row.data == bobs


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_draft_routes_need_a_session(client: TestClient, method: str) -> None:
    response = client.request(method, "/draft", json=PARTIAL)

    assert response.status_code == 401
