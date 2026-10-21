import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from core.auth import CurrentBorrower, CurrentSession, LoginFailed, verify_login
from core.db import SessionDep, engine
from core.storage import Base


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
def get_draft(borrower: CurrentBorrower) -> dict[str, Any] | None:
    if borrower.draft:
        return borrower.draft.data


def main() -> None:
    uvicorn.run("core.app:app", host=os.environ.get("HOST", "127.0.0.1"), port=8000)
