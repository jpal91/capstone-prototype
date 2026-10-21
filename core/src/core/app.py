import os
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import LoginFailed, verify_login
from core.db import engine, get_session
from core.storage import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="core", lifespan=lifespan)

# Makes the session commit or rollback before response goes out
SessionDep = Annotated[Session, Depends(get_session, scope="function")]


class LoginBody(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


@app.get("/health")
def health(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/login")
def login(session: SessionDep, login: LoginBody) -> LoginResponse:
    try:
        token_hash = verify_login(session, login.username, login.password)
        return LoginResponse(token=token_hash)
    except LoginFailed:
        raise HTTPException(
            status_code=401, detail="Invalid username or password"
        ) from None


def main() -> None:
    uvicorn.run("core.app:app", host=os.environ.get("HOST", "127.0.0.1"), port=8000)
