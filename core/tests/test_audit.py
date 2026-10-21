"""Hash-chained, append-only audit log (NFR-04), and what it can't catch (L-05).

Tampering tests switch the append-only trigger off first, as `core`'s own
database user can (L-06). Like everything else in a test, that is rolled back.
"""

import json
from itertools import pairwise
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from core.audit import GENESIS, append, entry_hash, verify_chain
from core.storage import AuditAction, AuditEvent


def append_several(db: Session, count: int) -> list[AuditEvent]:
    """Append `count` entries with varied fields, the way steps 5-7 will."""
    actions = list(AuditAction)
    return [
        append(
            db,
            actions[i % len(actions)],
            borrower_id=1,
            lender_id=i,
            version_id=1,
            grant_id=i,
            detail={"reason": "revoked", "n": i} if i % 2 else None,
        )
        for i in range(count)
    ]


def tamper(db: Session, sql: str, **params: Any) -> None:
    db.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
    db.execute(text(sql), params)
    db.expire_all()


# Building the chain


def test_first_entry_links_to_genesis(db: Session) -> None:
    event = append(db, AuditAction.Finalize, borrower_id=1, version_id=1)

    assert event.seq == 1
    assert event.prev_hash == GENESIS
    assert event.hash == entry_hash(event)
    assert event.detail == {}


def test_each_entry_links_to_the_one_before(db: Session) -> None:
    events = append_several(db, 4)

    assert [e.seq for e in events] == [1, 2, 3, 4]
    for before, after in pairwise(events):
        assert after.prev_hash == before.hash


def test_stored_entries_rehash_to_the_same_value(db: Session) -> None:
    # Catches anything that changes on the way through Postgres: timestamp
    # precision or timezone, JSONB key order, enum spelling.
    append(
        db,
        AuditAction.FetchDenied,
        lender_id=2,
        grant_id=7,
        detail={"reason": "expired", "z": [1, {"b": True, "a": "é"}]},
    )
    db.expire_all()

    stored = db.scalars(select(AuditEvent)).one()
    assert stored.hash == entry_hash(stored)


def test_rolled_back_append_leaves_no_gap(db: Session) -> None:
    append(db, AuditAction.Grant, grant_id=1)
    savepoint = db.begin_nested()
    append(db, AuditAction.Revoke, grant_id=1)
    savepoint.rollback()

    event = append(db, AuditAction.Fetch, grant_id=1)

    assert event.seq == 2


def test_append_takes_the_advisory_lock(db: Session) -> None:
    append(db, AuditAction.Grant)

    held = db.scalar(
        select(func.count())
        .select_from(text("pg_locks"))
        .where(text("locktype = 'advisory' AND pid = pg_backend_pid()"))
    )
    assert held >= 1


def test_a_fork_is_rejected_by_the_database(db: Session) -> None:
    first = append(db, AuditAction.Grant)
    fork = AuditEvent(
        seq=99,
        at=first.at,
        action=AuditAction.Revoke,
        detail={},
        prev_hash=first.prev_hash,
        hash="f" * 64,
    )

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(fork)
        db.flush()


# Verifying the chain


def test_empty_chain_verifies(db: Session) -> None:
    check = verify_chain(db)

    assert check.ok
    assert check.entries == 0


def test_clean_chain_verifies(db: Session) -> None:
    append_several(db, 5)

    check = verify_chain(db)

    assert check.ok
    assert check.entries == 5
    assert check.first_bad_seq is None


@pytest.mark.parametrize(
    ("sql", "params"),
    [
        ("UPDATE audit_event SET action = 'fetch' WHERE seq = 3", {}),
        (
            "UPDATE audit_event SET detail = CAST(:d AS jsonb) WHERE seq = 3",
            {"d": json.dumps({"reason": "other_lender"})},
        ),
        ("UPDATE audit_event SET at = at + interval '1 second' WHERE seq = 3", {}),
        ("UPDATE audit_event SET lender_id = 42 WHERE seq = 3", {}),
        ("UPDATE audit_event SET hash = repeat('a', 64) WHERE seq = 3", {}),
    ],
    ids=["action", "detail", "timestamp", "lender", "stored-hash"],
)
def test_altered_entry_is_caught_at_its_seq(
    db: Session, sql: str, params: dict[str, Any]
) -> None:
    append_several(db, 5)
    tamper(db, sql, **params)

    check = verify_chain(db)

    assert not check.ok
    assert check.first_bad_seq == 3


def test_patching_one_entry_and_the_next_link_is_caught(db: Session) -> None:
    # Because each hash covers prev_hash, re-hashing an altered entry changes
    # every later hash; fixing only the next entry's link isn't enough.
    append_several(db, 5)
    tamper(db, "UPDATE audit_event SET lender_id = 42 WHERE seq = 3")
    third = db.scalars(select(AuditEvent).where(AuditEvent.seq == 3)).one()
    tamper(
        db,
        "UPDATE audit_event SET hash = :h WHERE seq = 3",
        h=entry_hash(third),
    )
    tamper(
        db,
        "UPDATE audit_event SET prev_hash = :h WHERE seq = 4",
        h=entry_hash(third),
    )

    check = verify_chain(db)

    assert not check.ok
    assert check.first_bad_seq == 4


def test_deleted_middle_entry_is_caught(db: Session) -> None:
    append_several(db, 5)
    tamper(db, "DELETE FROM audit_event WHERE seq = 3")

    check = verify_chain(db)

    assert not check.ok
    assert check.first_bad_seq == 4


def test_swapped_entries_are_caught(db: Session) -> None:
    append_several(db, 5)
    # Three steps: the primary key is checked row by row, not per statement.
    tamper(db, "UPDATE audit_event SET seq = -1 WHERE seq = 2")
    tamper(db, "UPDATE audit_event SET seq = 2 WHERE seq = 3")
    tamper(db, "UPDATE audit_event SET seq = 3 WHERE seq = -1")

    check = verify_chain(db)

    assert not check.ok
    assert check.first_bad_seq == 2


# What the chain can't catch (L-05): these pass verification by design.


def test_l05_deleting_the_newest_entries_is_not_caught(db: Session) -> None:
    append_several(db, 5)
    tamper(db, "DELETE FROM audit_event WHERE seq > 3")

    check = verify_chain(db)

    assert check.ok
    assert check.entries == 3


def test_l05_a_rewritten_chain_is_not_caught(db: Session) -> None:
    append_several(db, 5)
    tamper(db, "UPDATE audit_event SET lender_id = 42 WHERE seq = 3")

    # Recompute every hash from the altered entry on, as an attacker with
    # write access could.
    prev_hash = db.scalar(select(AuditEvent.hash).where(AuditEvent.seq == 2))
    for event in db.scalars(
        select(AuditEvent).where(AuditEvent.seq >= 3).order_by(AuditEvent.seq)
    ):
        event.prev_hash = prev_hash
        event.hash = entry_hash(event)
        db.flush()
        prev_hash = event.hash

    assert verify_chain(db).ok


# Append-only in the database


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE audit_event SET lender_id = 42",
        "DELETE FROM audit_event",
        "TRUNCATE audit_event",
    ],
    ids=["update", "delete", "truncate"],
)
def test_trigger_blocks_changes(db: Session, sql: str) -> None:
    append(db, AuditAction.Grant)

    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text(sql))
