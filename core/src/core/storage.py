from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DDL, DateTime, Enum, ForeignKey, Index, String, event, func
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
    versions: Mapped[list["Version"]] = relationship(
        back_populates="borrower", order_by="Version.number"
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


# Shared trigger function: blocks UPDATE, DELETE, TRUNCATE on append-only table
APPEND_ONLY = DDL("""
CREATE OR REPLACE FUNCTION append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Table %% is append-only: %% blocked', TG_TABLE_NAME, TG_OP;
END $$;

""")


def triggers(table_name: str) -> DDL:
    return DDL(f"""\
CREATE TRIGGER no_update_delete
    BEFORE UPDATE OR DELETE ON {table_name}
    FOR EACH ROW EXECUTE FUNCTION append_only();

CREATE TRIGGER no_truncate
    BEFORE TRUNCATE ON {table_name}
    FOR EACH STATEMENT EXECUTE FUNCTION append_only();
""")


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


class Version(Base):
    __tablename__ = "version"
    __table_args__ = (
        Index("unq_borrower_id_number", "borrower_id", "number", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrower.id"))
    number: Mapped[int]
    xml: Mapped[bytes]
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    borrower: Mapped[Borrower] = relationship(back_populates="versions")


event.listen(Base.metadata, "before_create", APPEND_ONLY)
event.listen(AuditEvent.__table__, "after_create", triggers("audit_event"))
event.listen(Version.__table__, "after_create", triggers("version"))
