import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email.utils import format_datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from core.auth import CurrentBorrower, CurrentSession, LoginFailed, verify_login
from core.db import SessionDep, engine
from core.storage import Base, Draft
from mismo import UrlaDraft


def http_date(dt: datetime) -> str:
    return format_datetime(dt.astimezone(UTC), usegmt=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="core", lifespan=lifespan)


class LoginBody(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


@app.get("/health")
def health(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/auth/login")
def login(db: SessionDep, login: LoginBody) -> LoginResponse:
    try:
        token = verify_login(db, login.username, login.password)
        return LoginResponse(token=token)
    except LoginFailed:
        raise HTTPException(
            status_code=401, detail="Invalid username or password"
        ) from None


@app.post("/auth/logout", status_code=204)
def logout(db: SessionDep, auth: CurrentSession) -> None:
    db.delete(auth)


@app.get("/draft")
def get_draft(borrower: CurrentBorrower, response: Response) -> UrlaDraft:
    if borrower.draft is None:
        return UrlaDraft()

    response.headers["Last-Modified"] = http_date(borrower.draft.updated_at)
    return UrlaDraft.model_validate(borrower.draft.data)


@app.put("/draft", status_code=204)
def put_draft(db: SessionDep, borrower: CurrentBorrower, body: UrlaDraft) -> None:
    data = body.model_dump(mode="json", by_alias=True, exclude_none=True)
    stmt = insert(Draft).values(data=data, borrower_id=borrower.id)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Draft.borrower_id],
        set_={"data": data, "updated_at": func.now()},
    )
    db.execute(stmt)


def main() -> None:
    uvicorn.run("core.app:app", host=os.environ.get("HOST", "127.0.0.1"), port=8000)
