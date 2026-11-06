"""FR-05 to FR-08, NFR-03: who can fetch what, tested against core directly.

The portal and mock-lender aren't involved, so neither can hide a bug in core.
Each denial is compared with the reply for an unused ID, byte for byte: a lender
must not be able to tell another lender's grant from one that doesn't exist.
Whether the audit log records the real reason is checked with the audit log.
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import pytest

from support.clients import BorrowerClient, LenderClient
from support.data import ABSENT_ID, complete, expires_in
from support.settings import Settings


def status_of(alice: BorrowerClient, grant_id: int) -> dict[str, Any]:
    """The grant as the borrower sees it in GET /grants."""
    grants = alice.get("/grants")
    assert grants.status_code == 200
    return {grant["id"]: grant for grant in grants.json()}[grant_id]


def new_grant(alice: BorrowerClient, client_id: str, version_id: int, **delta) -> int:
    response = alice.create_grant(client_id, version_id, expires_in(**delta))
    assert response.status_code == 201
    return response.json()["id"]


def reply(response: httpx.Response) -> tuple[int, bytes, dict[str, str]]:
    """Everything a lender can see, except the time it was sent."""
    headers = {k: v for k, v in response.headers.items() if k != "date"}
    return response.status_code, response.content, headers


@dataclass(frozen=True)
class Shared:
    """One version, and a grant to Lender A in each state."""

    version: dict[str, Any]
    xml: bytes
    grants: dict[str, int]


@pytest.fixture(scope="module")
def shared(alice: BorrowerClient, lender_a: LenderClient) -> Shared:
    version = alice.must_finalize(complete())
    xml = alice.version_xml(version["id"])
    assert xml.status_code == 200

    active = new_grant(alice, "lender-a", version["id"], days=1)
    revoked = new_grant(alice, "lender-a", version["id"], days=1)
    assert alice.revoke(revoked).status_code == 200

    expired = new_grant(alice, "lender-a", version["id"], seconds=1.5)
    assert lender_a.fetch(expired).status_code == 200  # it worked until it expired
    deadline = time.monotonic() + 10
    while status_of(alice, expired)["status"] != "expired":
        assert time.monotonic() < deadline, "the grant never expired"
        time.sleep(0.1)

    return Shared(
        version,
        xml.content,
        {"active": active, "revoked": revoked, "expired": expired},
    )


@pytest.fixture(scope="module")
def denied(lender_a: LenderClient) -> tuple[int, bytes, dict[str, str]]:
    """What a denial looks like: the reply for a grant that doesn't exist."""
    response = lender_a.fetch(ABSENT_ID)
    assert response.status_code == 404
    return reply(response)


# FR-05: granting


@pytest.mark.req("FR-05")
def test_grant_records_lender_version_and_expiry(alice: BorrowerClient, shared: Shared):
    expires_at = expires_in(days=2)

    response = alice.create_grant("lender-b", shared.version["id"], expires_at)

    assert response.status_code == 201
    grant = response.json()
    assert grant["status"] == "active"
    assert grant["lenderName"] == "Lender B"
    assert grant["versionId"] == shared.version["id"]
    assert datetime.fromisoformat(grant["expiresAt"]) == datetime.fromisoformat(
        expires_at
    )


@pytest.mark.req("FR-05")
def test_only_granted_lenders_can_fetch(
    alice: BorrowerClient,
    lender_a: LenderClient,
    lender_b: LenderClient,
    lender_c: LenderClient,
    denied: tuple,
    shared: Shared,
):
    grant_a = new_grant(alice, "lender-a", shared.version["id"], days=1)
    grant_b = new_grant(alice, "lender-b", shared.version["id"], days=1)

    assert lender_a.fetch(grant_a).status_code == 200
    assert lender_b.fetch(grant_b).status_code == 200
    assert reply(lender_c.fetch(grant_a)) == denied
    assert reply(lender_c.fetch(grant_b)) == denied


@pytest.mark.req("FR-05")
def test_grant_stays_on_its_version(alice: BorrowerClient, lender_a: LenderClient):
    first = alice.must_finalize(complete(borrower={"firstName": "First"}))
    grant = new_grant(alice, "lender-a", first["id"], days=1)
    first_xml = alice.version_xml(first["id"]).content

    second = alice.must_finalize(complete(borrower={"firstName": "Second"}))

    assert alice.version_xml(second["id"]).content != first_xml
    assert lender_a.fetch(grant).content == first_xml


@pytest.mark.req("FR-05")
@pytest.mark.parametrize(
    "expires_at",
    ["2020-01-01T00:00:00+00:00", "2999-01-01T00:00:00"],
    ids=["in-the-past", "no-timezone"],
)
def test_grant_rejects_bad_expiry(
    alice: BorrowerClient, shared: Shared, expires_at: str
):
    response = alice.create_grant("lender-a", shared.version["id"], expires_at)

    assert response.status_code == 422


@pytest.mark.req("FR-05")
def test_grant_rejects_unknown_lender(alice: BorrowerClient, shared: Shared):
    response = alice.post(
        "/grants",
        json={
            "lenderId": ABSENT_ID,
            "versionId": shared.version["id"],
            "expiresAt": expires_in(days=1),
        },
    )

    assert response.status_code == 404


# FR-06: revoking


@pytest.mark.req("FR-06")
def test_revoke_stops_only_that_grant(
    alice: BorrowerClient,
    lender_a: LenderClient,
    lender_b: LenderClient,
    denied: tuple,
    shared: Shared,
):
    version_id = shared.version["id"]
    revoked = new_grant(alice, "lender-a", version_id, days=1)
    same_lender = new_grant(alice, "lender-a", version_id, days=1)
    other_lender = new_grant(alice, "lender-b", version_id, days=1)
    assert lender_a.fetch(revoked).status_code == 200

    response = alice.revoke(revoked)

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    assert reply(lender_a.fetch(revoked)) == denied
    assert lender_a.fetch(same_lender).status_code == 200
    assert lender_b.fetch(other_lender).status_code == 200


@pytest.mark.req("FR-06")
def test_revoking_twice_changes_nothing(alice: BorrowerClient, shared: Shared):
    grant = new_grant(alice, "lender-a", shared.version["id"], days=1)
    first = alice.revoke(grant)
    assert first.status_code == 200

    second = alice.revoke(grant)

    assert second.status_code == 200
    assert second.json()["status"] == "revoked"
    assert second.json()["revokedAt"] == first.json()["revokedAt"]


# FR-07, NFR-03: the consent matrix


@pytest.mark.req("FR-07")
def test_active_grant_returns_the_versions_exact_bytes(
    lender_a: LenderClient, shared: Shared
):
    response = lender_a.fetch(shared.grants["active"])

    assert response.status_code == 200
    assert response.content == shared.xml
    digest = hashlib.sha256(response.content).hexdigest()
    assert digest == response.headers["X-Content-SHA256"]
    assert digest == shared.version["sha256"]


@pytest.mark.req("FR-07")
@pytest.mark.parametrize("state", ["revoked", "expired"])
def test_own_grant_denied_when_no_longer_active(
    lender_a: LenderClient, shared: Shared, denied: tuple, state: str
):
    assert reply(lender_a.fetch(shared.grants[state])) == denied


@pytest.mark.req("FR-07", "NFR-03")
@pytest.mark.parametrize("state", ["active", "revoked", "expired"])
def test_other_lenders_grant_denied(
    lender_b: LenderClient, shared: Shared, denied: tuple, state: str
):
    assert reply(lender_b.fetch(shared.grants[state])) == denied


@pytest.mark.req("FR-07")
def test_unused_id_denied_the_same_for_each_lender(
    lender_b: LenderClient, denied: tuple
):
    assert reply(lender_b.fetch(ABSENT_ID)) == denied


@pytest.mark.req("FR-07", "NFR-03")
def test_lender_list_shows_only_its_own_active_grants(
    lender_a: LenderClient,
    lender_b: LenderClient,
    lender_c: LenderClient,
    shared: Shared,
):
    listed = {grant["grantId"]: grant for grant in lender_a.grants().json()}
    ids = shared.grants

    assert listed[ids["active"]]["sha256"] == shared.version["sha256"]
    assert ids["revoked"] not in listed
    assert ids["expired"] not in listed
    for other in (lender_b, lender_c):
        others = {grant["grantId"] for grant in other.grants().json()}
        assert others.isdisjoint(ids.values())


@pytest.mark.req("NFR-03")
@pytest.mark.parametrize(
    ("client_id", "secret_of"),
    [("lender-a", None), ("lender-a", "lender-b"), ("nobody", "lender-a")],
    ids=["wrong-secret", "another-lenders-secret", "unknown-client"],
)
def test_bad_lender_credentials_refused(
    config: Settings, shared: Shared, client_id: str, secret_of: str | None
):
    secret = config.secrets[secret_of] if secret_of else "wrong-secret"

    with LenderClient(config.core_url, client_id, secret) as client:
        assert client.grants().status_code == 401
        assert client.fetch(shared.grants["active"]).status_code == 401


@pytest.mark.req("NFR-03")
def test_lender_routes_refuse_no_credentials(anon: httpx.Client, shared: Shared):
    grant = shared.grants["active"]

    assert anon.get("/lender/grants").status_code == 401
    assert anon.get(f"/lender/grants/{grant}/application").status_code == 401


@pytest.mark.req("NFR-03")
def test_lender_routes_refuse_borrower_session(alice: BorrowerClient, shared: Shared):
    grant = shared.grants["active"]

    assert alice.get("/lender/grants").status_code == 401
    assert alice.get(f"/lender/grants/{grant}/application").status_code == 401


# FR-08: what the borrower sees


@pytest.mark.req("FR-08")
@pytest.mark.parametrize("state", ["active", "revoked", "expired"])
def test_grant_list_shows_status(alice: BorrowerClient, shared: Shared, state: str):
    assert status_of(alice, shared.grants[state])["status"] == state


@pytest.mark.req("FR-08")
def test_last_fetched_follows_successful_fetches(
    alice: BorrowerClient,
    lender_a: LenderClient,
    lender_b: LenderClient,
    shared: Shared,
):
    grant = new_grant(alice, "lender-a", shared.version["id"], days=1)
    assert status_of(alice, grant)["lastFetchedAt"] is None

    assert lender_b.fetch(grant).status_code == 404
    assert status_of(alice, grant)["lastFetchedAt"] is None  # a denial isn't a fetch

    assert lender_a.fetch(grant).status_code == 200
    first = status_of(alice, grant)["lastFetchedAt"]
    assert first is not None

    assert lender_a.fetch(grant).status_code == 200
    second = status_of(alice, grant)["lastFetchedAt"]
    assert datetime.fromisoformat(second) > datetime.fromisoformat(first)

    assert alice.revoke(grant).status_code == 200
    assert status_of(alice, grant)["lastFetchedAt"] == second  # history stays
