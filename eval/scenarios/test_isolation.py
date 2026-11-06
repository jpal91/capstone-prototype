"""NFR-08: borrower routes need a session, and borrowers only reach their own data."""

import re
from dataclasses import dataclass

import httpx
import pytest

from support.clients import BorrowerClient, LenderClient
from support.data import ABSENT_ID, complete, drop_nulls, expires_in

pytestmark = pytest.mark.req("NFR-08")

# Written out, so a new route that skips the session check can't go unnoticed:
# test_list_covers_every_borrower_route compares this with core's OpenAPI document.
BORROWER_ROUTES = [
    ("POST", "/auth/logout"),
    ("GET", "/draft"),
    ("PUT", "/draft"),
    ("POST", "/draft/finalize"),
    ("GET", "/versions"),
    ("GET", "/versions/{version_id}/xml"),
    ("GET", "/lenders"),
    ("GET", "/grants"),
    ("POST", "/grants"),
    ("POST", "/grants/{grant_id}/revoke"),
]
NOT_BORROWER_ROUTES = {"/health", "/auth/login"}

each_borrower_route = pytest.mark.parametrize(("method", "route"), BORROWER_ROUTES)


def fill_ids(route: str) -> str:
    return re.sub(r"\{\w+\}", "1", route)


@dataclass(frozen=True)
class Owned:
    version_id: int
    grant_id: int


def own_version_and_grant(borrower: BorrowerClient) -> Owned:
    version = borrower.must_finalize(complete())
    return Owned(version["id"], borrower.must_grant("lender-a", version["id"], days=1))


@pytest.fixture(scope="module")
def alices(alice: BorrowerClient) -> Owned:
    return own_version_and_grant(alice)


@pytest.fixture(scope="module")
def bobs(bob: BorrowerClient) -> Owned:
    return own_version_and_grant(bob)


def ids(response: httpx.Response) -> set[int]:
    assert response.status_code == 200
    return {item["id"] for item in response.json()}


def test_list_covers_every_borrower_route(anon: httpx.Client):
    spec = anon.get("/openapi.json").json()

    found = {
        (method.upper(), path)
        for path, operations in spec["paths"].items()
        for method in operations
        if path not in NOT_BORROWER_ROUTES and not path.startswith("/lender/")
    }

    assert found == set(BORROWER_ROUTES)


@each_borrower_route
def test_route_refuses_no_session(anon: httpx.Client, method: str, route: str):
    assert anon.request(method, fill_ids(route)).status_code == 401


@each_borrower_route
def test_route_refuses_unknown_token(anon: httpx.Client, method: str, route: str):
    headers = {"Authorization": "Bearer not-a-real-token"}

    response = anon.request(method, fill_ids(route), headers=headers)

    assert response.status_code == 401


@each_borrower_route
def test_route_refuses_lender_credentials(
    lender_a: LenderClient, method: str, route: str
):
    assert lender_a.request(method, fill_ids(route)).status_code == 401


def test_drafts_are_separate(alice: BorrowerClient, bob: BorrowerClient):
    """These routes take no ID: the session alone decides whose draft it is."""
    alices_draft = complete(borrower={"firstName": "Alice-side"})
    bobs_draft = complete(borrower={"firstName": "Bob-side"})

    assert alice.put_draft(alices_draft).status_code == 204
    assert bob.put_draft(bobs_draft).status_code == 204

    assert drop_nulls(alice.get("/draft").json()) == alices_draft
    assert drop_nulls(bob.get("/draft").json()) == bobs_draft


def test_lists_show_only_own_records(
    alice: BorrowerClient, bob: BorrowerClient, alices: Owned, bobs: Owned
):
    alices_versions, bobs_versions = (
        ids(alice.get("/versions")),
        ids(bob.get("/versions")),
    )
    alices_grants, bobs_grants = ids(alice.get("/grants")), ids(bob.get("/grants"))

    assert alices.version_id in alices_versions - bobs_versions
    assert bobs.version_id in bobs_versions - alices_versions
    assert alices.grant_id in alices_grants - bobs_grants
    assert bobs.grant_id in bobs_grants - alices_grants


def test_finalize_adds_only_to_own_versions(alice: BorrowerClient, bob: BorrowerClient):
    before = ids(alice.get("/versions"))

    bob.must_finalize(complete())

    assert ids(alice.get("/versions")) == before


def test_other_borrowers_version_looks_absent(
    alice: BorrowerClient, bob: BorrowerClient, alices: Owned
):
    """The same reply as an unused ID, so Bob can't tell the version exists."""
    assert alice.version_xml(alices.version_id).status_code == 200

    response = bob.version_xml(alices.version_id)

    assert response.status_code == 404
    assert response.content == bob.version_xml(ABSENT_ID).content


def test_cannot_grant_other_borrowers_version(bob: BorrowerClient, alices: Owned):
    expires_at = expires_in(days=1)
    before = ids(bob.get("/grants"))

    response = bob.create_grant("lender-a", alices.version_id, expires_at)

    assert response.status_code == 404
    absent = bob.create_grant("lender-a", ABSENT_ID, expires_at)
    assert response.content == absent.content
    assert ids(bob.get("/grants")) == before


def test_cannot_revoke_other_borrowers_grant(
    alice: BorrowerClient, bob: BorrowerClient, alices: Owned
):
    response = bob.revoke(alices.grant_id)

    assert response.status_code == 404
    assert response.content == bob.revoke(ABSENT_ID).content
    grants = {grant["id"]: grant for grant in alice.get("/grants").json()}
    assert grants[alices.grant_id]["status"] == "active"
    assert grants[alices.grant_id]["revokedAt"] is None
