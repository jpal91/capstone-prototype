"""NFR-04, L-05, L-06: the audit log, checked in core's database.

This is the one place eval/ looks inside a service, because the log has no route.
Tampering happens in transactions the `db` fixture rolls back, so the real log is
never changed. Each tamper test first disables the append-only trigger as core's
own database role, which is what L-06 says that role can do.
"""

from datetime import datetime
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from support.audit import entry_hash, first_bad_seq, read_chain
from support.clients import BorrowerClient, LenderClient
from support.data import ABSENT_ID, complete, expires_in


def last_seq(db: psycopg.Connection) -> int:
    return db.execute(
        "SELECT coalesce(max(seq), 0) AS seq FROM audit_event"
    ).fetchone()["seq"]


def entries_since(db: psycopg.Connection, seq: int) -> list[tuple]:
    """New entries as (action, borrower, lender, version, grant, detail)."""
    rows = db.execute(
        "SELECT * FROM audit_event WHERE seq > %s ORDER BY seq", (seq,)
    ).fetchall()
    return [
        (
            row["action"],
            row["borrower_id"],
            row["lender_id"],
            row["version_id"],
            row["grant_id"],
            row["detail"],
        )
        for row in rows
    ]


def unlock(db: psycopg.Connection) -> None:
    db.execute("ALTER TABLE audit_event DISABLE TRIGGER USER")


@pytest.fixture(scope="module")
def alice_id(core_db: psycopg.Connection) -> int:
    return core_db.execute(
        "SELECT id FROM borrower WHERE username = 'alice'"
    ).fetchone()["id"]


@pytest.fixture(scope="module")
def target(alice: BorrowerClient, lender_a: LenderClient) -> dict[str, Any]:
    """Real activity to tamper with: a fetch entry that has an entry after it."""
    version = alice.must_finalize(complete())
    grant = alice.must_grant("lender-a", version["id"], days=1)
    assert lender_a.fetch(grant).status_code == 200
    assert alice.revoke(grant).status_code == 200
    return {"version": version["id"], "grant": grant}


@pytest.fixture
def seq(target: dict[str, Any], db: psycopg.Connection) -> int:
    """The sequence number of the fetch entry to tamper with."""
    return db.execute(
        "SELECT seq FROM audit_event WHERE action = 'fetch' AND grant_id = %s",
        (target["grant"],),
    ).fetchone()["seq"]


# What gets recorded


@pytest.mark.req("NFR-04", "FR-07")
def test_each_action_adds_one_entry(
    alice: BorrowerClient,
    alice_id: int,
    lender_a: LenderClient,
    lender_b: LenderClient,
    db: psycopg.Connection,
):
    a, b = alice.lender_id("lender-a"), alice.lender_id("lender-b")
    start = last_seq(db)

    version = alice.must_finalize(complete())
    expires_at = expires_in(days=1)
    grant = alice.create_grant("lender-a", version["id"], expires_at).json()["id"]
    assert lender_a.fetch(grant).status_code == 200
    assert lender_b.fetch(grant).status_code == 404
    assert alice.revoke(grant).status_code == 200
    assert lender_a.fetch(grant).status_code == 404

    sha256 = {"sha256": version["sha256"]}
    v = version["id"]
    assert entries_since(db, start) == [
        ("finalize", alice_id, None, v, None, sha256),
        ("grant", alice_id, a, v, grant, {"expiresAt": expires_at}),
        ("fetch", alice_id, a, v, grant, sha256),
        ("fetch_denied", alice_id, b, v, grant, {"reason": "other_lender"}),
        ("revoke", alice_id, a, v, grant, {}),
        ("fetch_denied", alice_id, a, v, grant, {"reason": "revoked"}),
    ]


@pytest.mark.req("NFR-04", "FR-07")
def test_expired_denial_records_its_reason(
    alice: BorrowerClient,
    lender_a: LenderClient,
    db: psycopg.Connection,
):
    version = alice.must_finalize(complete())
    grant = alice.must_grant("lender-a", version["id"], seconds=1)
    alice.wait_until_expired(grant)
    start = last_seq(db)

    assert lender_a.fetch(grant).status_code == 404

    [(action, *_, detail)] = entries_since(db, start)
    assert (action, detail) == ("fetch_denied", {"reason": "expired"})


@pytest.mark.req("NFR-04", "FR-07")
def test_unused_id_denial_records_its_reason(
    alice: BorrowerClient, lender_a: LenderClient, db: psycopg.Connection
):
    start = last_seq(db)

    assert lender_a.fetch(ABSENT_ID).status_code == 404

    assert entries_since(db, start) == [
        (
            "fetch_denied",
            None,
            alice.lender_id("lender-a"),
            None,
            ABSENT_ID,
            {"reason": "not_found"},
        )
    ]


@pytest.mark.req("NFR-04")
def test_refused_actions_add_no_entries(
    alice: BorrowerClient,
    bob: BorrowerClient,
    target: dict[str, Any],
    db: psycopg.Connection,
):
    start = last_seq(db)

    assert alice.put_draft({}).status_code == 204
    assert alice.finalize().status_code == 422  # incomplete
    assert bob.revoke(target["grant"]).status_code == 404
    expires_at = expires_in(days=1)
    assert (
        bob.create_grant("lender-a", target["version"], expires_at).status_code == 404
    )
    assert alice.revoke(target["grant"]).status_code == 200  # already revoked

    assert entries_since(db, start) == []


@pytest.mark.req("FR-08", "NFR-04")
def test_last_fetched_is_the_logged_fetch_time(
    alice: BorrowerClient,
    lender_a: LenderClient,
    db: psycopg.Connection,
):
    version = alice.must_finalize(complete())
    grant = alice.must_grant("lender-a", version["id"], days=1)
    assert lender_a.fetch(grant).status_code == 200

    logged = db.execute(
        "SELECT at FROM audit_event WHERE action = 'fetch' AND grant_id = %s", (grant,)
    ).fetchone()["at"]

    assert datetime.fromisoformat(alice.view_grant(grant)["lastFetchedAt"]) == logged


# The chain


@pytest.mark.req("NFR-04")
def test_whole_chain_verifies(target: dict[str, Any], db: psycopg.Connection):
    chain = read_chain(db)

    assert chain
    assert first_bad_seq(chain) is None


# What the database refuses


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        pytest.param(
            "UPDATE audit_event SET detail = '{}'",
            "append-only",
            marks=pytest.mark.req("NFR-04"),
            id="update-audit",
        ),
        pytest.param(
            "DELETE FROM audit_event",
            "append-only",
            marks=pytest.mark.req("NFR-04"),
            id="delete-audit",
        ),
        pytest.param(
            "TRUNCATE audit_event",
            "append-only",
            marks=pytest.mark.req("NFR-04"),
            id="truncate-audit",
        ),
        pytest.param(
            "UPDATE version SET sha256 = repeat('0', 64)",
            "append-only",
            marks=pytest.mark.req("FR-02"),
            id="update-version",
        ),
        pytest.param(
            "DELETE FROM version",
            "append-only",
            marks=pytest.mark.req("FR-02"),
            id="delete-version",
        ),
        pytest.param(
            "TRUNCATE version CASCADE",
            "append-only",
            marks=pytest.mark.req("FR-02"),
            id="truncate-version",
        ),
        pytest.param(
            "UPDATE access_grant SET expires_at = expires_at + interval '1 year'",
            "only allowed change",
            marks=pytest.mark.req("FR-05"),
            id="extend-grant",
        ),
        pytest.param(
            "UPDATE access_grant SET revoked_at = NULL WHERE revoked_at IS NOT NULL",
            "only allowed change",
            marks=pytest.mark.req("FR-06"),
            id="unrevoke-grant",
        ),
        pytest.param(
            "DELETE FROM access_grant",
            "never deleted",
            marks=pytest.mark.req("FR-06"),
            id="delete-grant",
        ),
    ],
)
def test_database_refuses_changes_to_records(
    target: dict[str, Any], db: psycopg.Connection, statement: str, message: str
):
    with pytest.raises(psycopg.errors.RaiseException, match=message):
        db.execute(statement)


@pytest.mark.req("L-06")
def test_core_role_can_disable_the_trigger(seq: int, db: psycopg.Connection):
    """L-06: the trigger stops mistakes, not core's own database role."""
    assert db.execute("SELECT current_user AS role").fetchone()["role"] == "core"

    unlock(db)
    changed = db.execute("UPDATE audit_event SET detail = '{}' WHERE seq = %s", (seq,))

    assert changed.rowcount == 1


# Tampering the chain detects


@pytest.mark.req("NFR-04", "L-05")
@pytest.mark.parametrize(
    "change",
    [
        'detail = detail || \'{"sha256": "forged"}\'',
        "at = at + interval '1 second'",
        "action = 'revoke'",
        "lender_id = NULL",
        "hash = repeat('0', 64)",
    ],
    ids=["detail", "timestamp", "action", "lender", "stored-hash"],
)
def test_edited_entry_is_detected(seq: int, db: psycopg.Connection, change: str):
    unlock(db)

    db.execute(f"UPDATE audit_event SET {change} WHERE seq = %s", (seq,))

    assert first_bad_seq(read_chain(db)) == seq


@pytest.mark.req("NFR-04", "L-05")
def test_edited_entry_with_fresh_hash_is_detected_by_the_next(
    seq: int, db: psycopg.Connection
):
    """Fixing the entry's own hash doesn't help: the next entry stored the old one."""
    unlock(db)
    entry = next(e for e in read_chain(db) if e["seq"] == seq)
    entry["detail"] = {"sha256": "forged"}

    db.execute(
        "UPDATE audit_event SET detail = %s, hash = %s WHERE seq = %s",
        (Jsonb(entry["detail"]), entry_hash(entry), seq),
    )

    assert first_bad_seq(read_chain(db)) == seq + 1


@pytest.mark.req("NFR-04", "L-05")
def test_deleted_entry_is_detected(seq: int, db: psycopg.Connection):
    unlock(db)

    db.execute("DELETE FROM audit_event WHERE seq = %s", (seq,))

    assert first_bad_seq(read_chain(db)) == seq + 1


@pytest.mark.req("NFR-04", "L-05")
def test_deleted_first_entry_is_detected(target: dict, db: psycopg.Connection):
    unlock(db)

    db.execute("DELETE FROM audit_event WHERE seq = 1")

    assert first_bad_seq(read_chain(db)) == 2


@pytest.mark.req("NFR-04", "L-05")
def test_reordered_entries_are_detected(seq: int, db: psycopg.Connection):
    unlock(db)
    swap = "UPDATE audit_event SET seq = %s WHERE seq = %s"

    db.execute(swap, (-1, seq))
    db.execute(swap, (seq, seq + 1))
    db.execute(swap, (seq + 1, -1))

    assert first_bad_seq(read_chain(db)) == seq


# Tampering the chain can't detect (L-05)


@pytest.mark.req("L-05")
def test_deleting_the_newest_entries_goes_undetected(seq: int, db: psycopg.Connection):
    head = read_chain(db)[-1]["hash"]
    unlock(db)

    deleted = db.execute("DELETE FROM audit_event WHERE seq > %s", (seq,))

    assert deleted.rowcount > 0
    chain = read_chain(db)
    assert first_bad_seq(chain) is None
    assert chain[-1]["hash"] != head  # a head kept outside the database would notice


@pytest.mark.req("L-05")
def test_rewriting_the_chain_goes_undetected(seq: int, db: psycopg.Connection):
    chain = read_chain(db)
    head = chain[-1]["hash"]
    unlock(db)

    previous = None
    for entry in chain:
        if entry["seq"] < seq:
            continue
        if entry["seq"] == seq:
            entry["detail"] = {"sha256": "forged"}
        else:
            entry["prev_hash"] = previous
        previous = entry_hash(entry)
        db.execute(
            "UPDATE audit_event SET detail = %s, prev_hash = %s, hash = %s"
            " WHERE seq = %s",
            (Jsonb(entry["detail"]), entry["prev_hash"], previous, entry["seq"]),
        )

    rewritten = read_chain(db)
    assert first_bad_seq(rewritten) is None
    assert next(e for e in rewritten if e["seq"] == seq)["detail"] == {
        "sha256": "forged"
    }
    assert (
        rewritten[-1]["hash"] != head
    )  # a head kept outside the database would notice
