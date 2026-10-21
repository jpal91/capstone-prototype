import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core.storage import AuthSession, Borrower

HASHER = PasswordHash.recommended()
DUMMY_HASH = HASHER.hash("timing-equalizer")
SESSION_LIFETIME = timedelta(hours=24)


class LoginFailed(Exception):
    pass


def verify_login(db: Session, username: str, pwd: str) -> str:
    borrower_stmt = select(Borrower).where(Borrower.username == username)
    borrower = db.scalars(borrower_stmt).first()

    if borrower is None:
        # Hides the fact that the username wasn't found by adding extra time
        HASHER.verify(pwd, DUMMY_HASH)
        raise LoginFailed

    if not HASHER.verify(pwd, borrower.password_hash):
        raise LoginFailed

    new_token = secrets.token_urlsafe(32)
    token_hash = sha256(new_token.encode()).digest()
    updates = datetime.now(UTC)
    expires = updates + SESSION_LIFETIME

    stmt = insert(AuthSession).values(
        token_hash=token_hash,
        borrower_id=borrower.id,
        expires_at=expires,
        update_at=updates,
    )

    # One session per borrower, logging in again will invalidate previous sessions
    stmt = stmt.on_conflict_do_update(
        index_elements=[AuthSession.borrower_id],
        set_={"token_hash": token_hash, "update_at": updates, "expires_at": expires},
    )

    db.execute(stmt)

    return new_token
