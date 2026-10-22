"""Create the tables and the synthetic demo accounts (NFR-06).

Credentials come from the environment; compose.yml supplies demo defaults.
Safe to run again: existing accounts are updated in place, so changing a
password or secret in the environment and re-seeding applies it.

Only accounts are seeded. Drafts, versions, and grants are made through the
API, so each has its audit entry.
"""

import os
import sys
from collections.abc import Mapping

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core.auth import HASHER, hash_token
from core.db import SessionLocal, engine
from core.storage import Base, Borrower, Lender

# username -> environment variable holding the password
BORROWERS = {
    "alice": "ALICE_PASSWORD",
    "bob": "BOB_PASSWORD",
}

# (name, client_id, environment variable holding the client secret)
LENDERS = [
    ("Lender A", "lender-a", "LENDER_A_SECRET"),
    ("Lender B", "lender-b", "LENDER_B_SECRET"),
    ("Lender C", "lender-c", "LENDER_C_SECRET"),
]

REQUIRED = [*BORROWERS.values(), *(var for _, _, var in LENDERS)]


def seed(db: Session, env: Mapping[str, str]) -> None:
    for username, var in BORROWERS.items():
        stmt = insert(Borrower).values(
            username=username, password_hash=HASHER.hash(env[var])
        )
        db.execute(
            stmt.on_conflict_do_update(
                index_elements=[Borrower.username],
                set_={"password_hash": stmt.excluded.password_hash},
            )
        )

    for name, client_id, var in LENDERS:
        stmt = insert(Lender).values(
            name=name, client_id=client_id, hashed_secret=hash_token(env[var])
        )
        db.execute(
            stmt.on_conflict_do_update(
                index_elements=[Lender.client_id],
                set_={
                    "name": stmt.excluded.name,
                    "hashed_secret": stmt.excluded.hashed_secret,
                },
            )
        )


def main() -> None:
    missing = [var for var in REQUIRED if not os.environ.get(var)]
    if missing:
        sys.exit(
            f"core-seed: missing {', '.join(missing)}. "
            "compose.yml sets demo values; when running natively, set them in .env."
        )

    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        seed(db, os.environ)

    print(
        f"core-seed: {len(BORROWERS)} borrowers "
        f"({', '.join(BORROWERS)}), {len(LENDERS)} lenders "
        f"({', '.join(client_id for _, client_id, _ in LENDERS)})"
    )
