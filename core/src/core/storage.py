from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


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


class Lender(Base):
    __tablename__ = "lender"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    client_id: Mapped[str] = mapped_column(unique=True)
    hashed_secret: Mapped[bytes]


class AuditAction(StrEnum):
    Finalize = "finalize"
    Grant = "grant"
    Revoke = "revoke"
    Fetch = "fetch"
    FetchDenied = "fetch_denied"


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_grant", "grant_id", "seq"),)

    seq: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    borrower_id: Mapped[int | None]
    lender_id: Mapped[int | None]
    version_id: Mapped[int | None]
    grant_id: Mapped[int | None]
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(String(64), unique=True)
    hash: Mapped[str] = mapped_column(String(64))
