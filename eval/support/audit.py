"""A verifier for core's audit chain that doesn't use core.audit.

It's written from the format in ADR 0004, so a bug in core's own verifier can't
hide a broken chain. The JSON key names and timestamp format aren't in the ADR
and had to come from core; the hash and the checks are this file's own.
"""

import hashlib
import json
from datetime import UTC
from typing import Any

import psycopg

GENESIS = "0" * 64

Entry = dict[str, Any]


def read_chain(db: psycopg.Connection) -> list[Entry]:
    return db.execute("SELECT * FROM audit_event ORDER BY seq").fetchall()


def entry_hash(entry: Entry) -> str:
    """SHA-256(prev_hash + canonical JSON of the entry), from ADR 0004."""
    body = {
        "seq": entry["seq"],
        "at": entry["at"].astimezone(UTC).isoformat(),
        "action": entry["action"],
        "borrower_id": entry["borrower_id"],
        "lender_id": entry["lender_id"],
        "version_id": entry["version_id"],
        "grant_id": entry["grant_id"],
        "detail": entry["detail"],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((entry["prev_hash"] + canonical).encode()).hexdigest()


def first_bad_seq(chain: list[Entry]) -> int | None:
    """The first entry that doesn't link or doesn't match its hash, if any."""
    previous = GENESIS
    for entry in chain:
        if entry["prev_hash"] != previous or entry["hash"] != entry_hash(entry):
            return entry["seq"]
        previous = entry["hash"]
    return None
