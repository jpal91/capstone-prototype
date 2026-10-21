import hashlib
from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from core.audit import append
from core.storage import AuditAction, Borrower, Draft, Version
from mismo import Urla, UrlaDraft, to_xml, validate


class ResponseBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True
    )


class VersionItemResponse(ResponseBase):
    id: int
    number: int
    sha256: str
    created_at: datetime


def add_new_draft_service(db: Session, borrower: Borrower, body: UrlaDraft) -> None:
    data = body.model_dump(mode="json", by_alias=True, exclude_none=True)
    stmt = insert(Draft).values(data=data, borrower_id=borrower.id)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Draft.borrower_id],
        set_={"data": data, "updated_at": func.now()},
    )
    db.execute(stmt)


def finalize_draft_service(db: Session, borrower: Borrower) -> VersionItemResponse:
    if not borrower.draft:
        raise HTTPException(422, detail="Borrower draft does not exist")

    try:
        urla = Urla.model_validate(borrower.draft.data)
    except ValidationError as e:
        raise HTTPException(
            422, detail=e.errors(include_url=False, include_context=False)
        ) from None

    xml = to_xml(urla)
    validate(xml)

    stmt = (
        select(func.count())
        .select_from(Version)
        .where(Version.borrower_id == borrower.id)
    )
    count = db.execute(stmt).one()[0]

    sha256 = hashlib.sha256(xml).hexdigest()
    number = count + 1

    stmt = (
        insert(Version)
        .values(
            borrower_id=borrower.id,
            number=number,
            xml=xml,
            sha256=sha256,
        )
        .returning(Version.id, Version.created_at)
    )

    version_id, created_at = db.execute(stmt).one()

    append(
        db,
        AuditAction.Finalize,
        borrower_id=borrower.id,
        version_id=version_id,
        detail={"sha256": sha256},
    )

    return VersionItemResponse(
        id=version_id, number=number, sha256=sha256, created_at=created_at
    )


def all_versions_service(db: Session, borrower: Borrower) -> list[VersionItemResponse]:
    stmt = (
        select(Version.id, Version.number, Version.sha256, Version.created_at)
        .where(Version.borrower_id == borrower.id)
        .order_by(Version.number)
    )

    res = db.execute(stmt).all()

    return [
        VersionItemResponse(id=r[0], number=r[1], sha256=r[2], created_at=r[3])
        for r in res
    ]


def version_xml_service(
    db: Session, borrower: Borrower, version_id: int
) -> tuple[str, bytes]:
    stmt = (
        select(Version.sha256, Version.xml)
        .select_from(Version)
        .where(Version.id == version_id, Version.borrower_id == borrower.id)
    )

    try:
        res = db.execute(stmt).one()
    except NoResultFound:
        raise HTTPException(404, detail="Version id not found")

    return res
