import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email.utils import format_datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from core.auth import (
    CurrentBorrower,
    CurrentLender,
    CurrentSession,
    LoginFailed,
    verify_login,
)
from core.db import SessionDep, engine
from core.services import (
    GrantCreateBody,
    GrantResponse,
    LenderGrantResponse,
    LenderResponse,
    VersionItemResponse,
    add_new_draft_service,
    all_grants_service,
    all_versions_service,
    finalize_draft_service,
    get_application_service,
    grant_create_service,
    grant_revoke_service,
    lender_grants_service,
    lenders_service,
    version_xml_service,
)
from core.storage import Base
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


class FieldError(BaseModel):
    type: str
    loc: list[str | int]
    msg: str


class ValidationErrorBody(BaseModel):
    """The body FastAPI sends for a RequestValidationError."""

    detail: list[FieldError]


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
    add_new_draft_service(db, borrower, body)


@app.post(
    "/draft/finalize",
    status_code=201,
    responses={422: {"model": ValidationErrorBody}},
)
def finalize_draft(db: SessionDep, borrower: CurrentBorrower) -> VersionItemResponse:
    return finalize_draft_service(db, borrower)


@app.get("/versions")
def versions(db: SessionDep, borrower: CurrentBorrower) -> list[VersionItemResponse]:
    return all_versions_service(db, borrower)


@app.get(
    "/versions/{version_id}/xml",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
def version_xml(db: SessionDep, borrower: CurrentBorrower, version_id: int) -> Response:
    sha256, xml = version_xml_service(db, borrower, version_id)

    return Response(
        xml, media_type="application/xml", headers={"X-Content-SHA256": sha256}
    )


@app.get("/lenders")
def lenders(db: SessionDep, _borrower: CurrentBorrower) -> list[LenderResponse]:
    return lenders_service(db)


@app.get("/lender/grants")
def lender_grants(db: SessionDep, lender: CurrentLender) -> list[LenderGrantResponse]:
    return lender_grants_service(db, lender)


NOT_FOUND = {"detail": "Not Found"}


@app.get(
    "/lender/grants/{grant_id}/application",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
def get_application(db: SessionDep, lender: CurrentLender, grant_id: int) -> Response:
    result = get_application_service(db, lender, grant_id)

    if result is None:
        # Returned, not raised: raising would roll back the fetch_denied entry.
        return JSONResponse(NOT_FOUND, status_code=404)

    xml, sha256 = result

    return Response(
        xml, media_type="application/xml", headers={"X-Content-SHA256": sha256}
    )


@app.get("/grants")
def grants(db: SessionDep, borrower: CurrentBorrower) -> list[GrantResponse]:
    return all_grants_service(db, borrower)


@app.post("/grants", status_code=201)
def create_grant(
    db: SessionDep, borrower: CurrentBorrower, grant: GrantCreateBody
) -> GrantResponse:
    return grant_create_service(db, borrower, grant)


@app.post("/grants/{grant_id}/revoke")
def revoke_grant(
    db: SessionDep, borrower: CurrentBorrower, grant_id: int
) -> GrantResponse:
    return grant_revoke_service(db, borrower, grant_id)


def main() -> None:
    uvicorn.run("core.app:app", host=os.environ.get("HOST", "127.0.0.1"), port=8000)
