from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.db import engine, get_session
from core.storage import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="core", lifespan=lifespan)

# Makes the session commit or rollback before response goes out
SessionDep = Annotated[Session, Depends(get_session, scope="function")]


@app.get("/health")
def health(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
