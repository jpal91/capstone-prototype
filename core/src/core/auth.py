import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core.db import SessionDep
from core.storage import AuthSession, Borrower

HASHER = PasswordHash.recommended()
DUMMY_HASH = HASHER.hash("timing-equalizer")
SESSION_LIFETIME = timedelta(hours=24)

bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


class LoginFailed(Exception):
    pass


def hash_token(token: str) -> bytes:
    return sha256(token.encode()).digest()


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
    token_hash = hash_token(new_token)
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


def current_session(db: SessionDep, creds: Credentials) -> AuthSession:
    if creds is not None:
        auth = db.scalars(
            select(AuthSession).where(
                AuthSession.token_hash == hash_token(creds.credentials),
                AuthSession.expires_at > func.now(),
            )
        ).first()

        if auth is not None:
            return auth

    raise HTTPException(
        401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )


CurrentSession = Annotated[AuthSession, Depends(current_session)]


def current_borrower(auth: CurrentSession) -> Borrower:
    return auth.borrower


CurrentBorrower = Annotated[Borrower, Depends(current_borrower)]
