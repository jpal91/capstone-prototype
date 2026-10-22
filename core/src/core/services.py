import hashlib
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    ValidationError,
)
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from core.audit import append
from core.storage import (
    AuditAction,
    Borrower,
    Draft,
    Grant,
    Lender,
    Version,
)
from mismo import Urla, UrlaDraft, to_xml, validate


class ServicesBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True
    )


class VersionItemResponse(ServicesBase):
    id: int
    number: int
    sha256: str
    created_at: datetime


class LenderResponse(ServicesBase):
    id: int
    name: str


def _in_future(dt: datetime) -> datetime:
    if dt <= datetime.now(UTC):
        raise ValueError("expiresAt must be in the future")
    return dt


class GrantCreateBody(ServicesBase):
    lender_id: int
    version_id: int
    expires_at: Annotated[AwareDatetime, AfterValidator(_in_future)]


class GrantResponse(ServicesBase):
    id: int
    status: Literal["active", "revoked", "expired"]
    expires_at: datetime
    created_at: datetime
    lender_id: int
    lender_name: str
    version_id: int
    version_number: int
    revoked_at: datetime | None = None


class LenderGrantResponse(ServicesBase):
    grant_id: int
    expires_at: datetime
    sha256: str


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


def lenders_service(db: Session) -> list[LenderResponse]:
    res = db.execute(select(Lender.id, Lender.name).order_by(Lender.name)).all()

    return [LenderResponse(id=r[0], name=r[1]) for r in res]


def lender_grants_service(db: Session, lender: Lender) -> list[LenderGrantResponse]:
    stmt = (
        select(Grant.id, Grant.expires_at, Version.sha256)
        .join(Grant.version)
        .where(Grant.grant_status() == "active", Grant.lender_id == lender.id)
        .order_by(Grant.id)
    )

    res = db.execute(stmt).all()

    return [LenderGrantResponse.model_validate(r._mapping) for r in res]


def get_application_service(
    db: Session, lender: Lender, grant_id: int
) -> tuple[bytes, str] | None:
    ids = {"grant_id": grant_id, "lender_id": lender.id}
    stmt = (
        select(
            Grant.grant_status().label("status"),
            Version.xml,
            Version.sha256,
            Grant.lender_id,
            Grant.borrower_id,
            Grant.version_id,
        )
        .join(Grant.version)
        .where(Grant.id == grant_id)
        .with_for_update(read=True, of=Grant)
    )

    try:
        grant = db.execute(stmt).one()
    except NoResultFound:
        append(db, AuditAction.FetchDenied, detail={"reason": "not_found"}, **ids)
        return None

    status, xml, sha, lid, bid, vid = grant

    ids = {**ids, "version_id": vid, "borrower_id": bid}

    reason = None

    if lid != lender.id:
        reason = "other_lender"
    elif status == "expired":
        reason = "expired"
    elif status == "revoked":
        reason = "revoked"

    if reason is not None:
        append(db, AuditAction.FetchDenied, detail={"reason": reason}, **ids)
        return None

    append(db, AuditAction.Fetch, detail={"sha256": sha}, **ids)

    return xml, sha


def grant_create_service(
    db: Session, borrower: Borrower, grant: GrantCreateBody
) -> GrantResponse:
    # Check version belongs to borrower
    try:
        version_id, version_number = db.execute(
            select(Version.id, Version.number).where(
                Version.id == grant.version_id, Version.borrower_id == borrower.id
            )
        ).one()
    except NoResultFound:
        raise HTTPException(404, detail="Version not found") from None

    # Check lender exists
    try:
        lender_id, lender_name = db.execute(
            select(Lender.id, Lender.name).where(Lender.id == grant.lender_id)
        ).one()
    except NoResultFound:
        raise HTTPException(404, detail="Lender not found") from None

    grant_stmt = (
        insert(Grant)
        .values(
            borrower_id=borrower.id,
            lender_id=grant.lender_id,
            version_id=grant.version_id,
            expires_at=grant.expires_at,
        )
        .returning(Grant.id, Grant.created_at)
    )

    grant_id, created_at = db.execute(grant_stmt).one()

    append(
        db,
        AuditAction.Grant,
        borrower_id=borrower.id,
        lender_id=grant.lender_id,
        version_id=grant.version_id,
        grant_id=grant_id,
        detail={"expiresAt": grant.expires_at.astimezone(UTC).isoformat()},
    )

    return GrantResponse(
        id=grant_id,
        status="active",
        expires_at=grant.expires_at,
        created_at=created_at,
        lender_id=lender_id,
        lender_name=lender_name,
        version_id=version_id,
        version_number=version_number,
    )


def _grants_query():
    return (
        select(
            Grant.id,
            Grant.grant_status().label("status"),
            Grant.expires_at,
            Grant.created_at,
            Grant.revoked_at,
            Lender.id.label("lender_id"),
            Lender.name.label("lender_name"),
            Version.id.label("version_id"),
            Version.number.label("version_number"),
        )
        .join(Grant.lender)
        .join(Grant.version)
    )


def _grant_response(row) -> GrantResponse:
    return GrantResponse.model_validate(row._mapping)  # matched by name


def all_grants_service(db: Session, borrower: Borrower) -> list[GrantResponse]:
    stmt = _grants_query().where(Grant.borrower_id == borrower.id).order_by(Grant.id)

    res = db.execute(stmt).all()

    return [_grant_response(r) for r in res]


def grant_revoke_service(
    db: Session, borrower: Borrower, grant_id: int
) -> GrantResponse:
    stmt = (
        update(Grant)
        .values(revoked_at=func.now())
        .where(
            Grant.id == grant_id,
            Grant.borrower_id == borrower.id,
            Grant.revoked_at.is_(None),
        )
        .returning(Grant.revoked_at)
    )

    revoked_at = db.scalar(stmt)

    stmt = _grants_query().where(Grant.id == grant_id, Grant.borrower_id == borrower.id)

    try:
        grant = db.execute(stmt).one()
    except NoResultFound:
        raise HTTPException(404, detail="Grant not found") from None

    res = _grant_response(grant)

    if revoked_at is None:
        return res

    append(
        db,
        AuditAction.Revoke,
        borrower_id=borrower.id,
        lender_id=res.lender_id,
        version_id=res.version_id,
        grant_id=res.id,
        detail={},
    )

    return res
