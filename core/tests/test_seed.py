"""The demo seed (NFR-06, NFR-07): accounts that work, and safe to run again."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core import seed as seed_module
from core.seed import BORROWERS, LENDERS, REQUIRED, seed
from core.storage import AuditEvent, Borrower, Grant, Lender

ENV = {var: f"{var.lower()}-test-value" for var in REQUIRED}


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_seeded_borrowers_can_log_in(client: TestClient, db: Session) -> None:
    seed(db, ENV)

    for username, var in BORROWERS.items():
        response = client.post(
            "/auth/login", json={"username": username, "password": ENV[var]}
        )
        assert response.status_code == 200, username


def test_seeded_lenders_can_authenticate(client: TestClient, db: Session) -> None:
    seed(db, ENV)

    for _, client_id, var in LENDERS:
        response = client.get("/lender/grants", auth=(client_id, ENV[var]))
        assert response.status_code == 200, client_id
        assert response.json() == []


def test_seeding_twice_updates_in_place(client: TestClient, db: Session) -> None:
    seed(db, ENV)
    changed = {**ENV, "ALICE_PASSWORD": "changed", "LENDER_A_SECRET": "changed"}

    seed(db, changed)

    assert count(db, Borrower) == len(BORROWERS)
    assert count(db, Lender) == len(LENDERS)
    old = client.post(
        "/auth/login", json={"username": "alice", "password": ENV["ALICE_PASSWORD"]}
    )
    new = client.post("/auth/login", json={"username": "alice", "password": "changed"})
    assert (old.status_code, new.status_code) == (401, 200)
    assert client.get("/lender/grants", auth=("lender-a", "changed")).status_code == 200


def test_seed_creates_no_grants_or_audit_entries(db: Session) -> None:
    seed(db, ENV)

    assert count(db, Grant) == 0
    assert count(db, AuditEvent) == 0


def test_missing_credentials_stop_the_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in REQUIRED:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ALICE_PASSWORD", "set")

    with pytest.raises(SystemExit, match="missing BOB_PASSWORD"):
        seed_module.main()
