from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.storage import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal.begin() as session:
        yield session
