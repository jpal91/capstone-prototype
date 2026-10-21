from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Borrower(Base):
    __tablename__ = "borrower"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str]

    draft: Mapped["Draft | None"] = relationship(
        back_populates="borrower", cascade="all, delete-orphan"
    )
    session: Mapped["AuthSession | None"] = relationship(
        back_populates="borrower", cascade="all, delete-orphan"
    )


class Draft(Base):
    __tablename__ = "draft"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrower.id"), unique=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    borrower: Mapped["Borrower"] = relationship(back_populates="draft")


class AuthSession(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrower.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    borrower: Mapped["Borrower"] = relationship(back_populates="session")
