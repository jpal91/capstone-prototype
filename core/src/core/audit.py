import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.storage import AuditAction, AuditEvent

AUDIT_LOCK = 0x41554449545F4C4B  # "AUDIT_LK"
GENESIS = "0" * 64


def entry_hash(event: AuditEvent) -> str:
    body = {
        "seq": event.seq,
        "at": event.at.astimezone(UTC).isoformat(),
        "action": event.action,
        "borrower_id": event.borrower_id,
        "lender_id": event.lender_id,
        "version_id": event.version_id,
        "grant_id": event.grant_id,
        "detail": event.detail,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((event.prev_hash + canonical).encode()).hexdigest()


def append(
    db: Session,
    action: AuditAction,
    *,
    borrower_id: int | None = None,
    lender_id: int | None = None,
    version_id: int | None = None,
    grant_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    detail = detail or {}
    db.execute(select(func.pg_advisory_xact_lock(AUDIT_LOCK)))

    last = db.execute(
        select(AuditEvent.seq, AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1)
    ).first()
    seq, prev_hash = (last.seq + 1, last.hash) if last else (1, GENESIS)

    event = AuditEvent(
        seq=seq,
        at=datetime.now(UTC),
        action=action,
        borrower_id=borrower_id,
        lender_id=lender_id,
        version_id=version_id,
        grant_id=grant_id,
        detail=detail,
        prev_hash=prev_hash,
    )
    event.hash = entry_hash(event)
    db.add(event)
    db.flush()

    return event


class ChainCheck(BaseModel):
    ok: bool
    entries: int
    first_bad_seq: int | None = None


def verify_chain(db: Session) -> ChainCheck:
    chain = db.scalars(select(AuditEvent).order_by(AuditEvent.seq)).all()
    prev_hash = GENESIS
    n = len(chain)

    for event in chain:
        if event.prev_hash != prev_hash:
            return ChainCheck(ok=False, entries=n, first_bad_seq=event.seq)

        expected = entry_hash(event)

        if event.hash != expected:
            return ChainCheck(ok=False, entries=n, first_bad_seq=event.seq)

        prev_hash = expected

    return ChainCheck(ok=True, entries=n)
