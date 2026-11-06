"""L-01: revoking stops future fetches but can't take back a copy already fetched.

This goes through mock-lender, which keeps its copies in its own database and
reaches core only through the lender API, as a lender's own system would.
"""

from typing import Any

import httpx
import pytest

from support.clients import BorrowerClient, LenderClient, reply
from support.data import ABSENT_ID, complete, expires_in


def new_grant(alice: BorrowerClient, client_id: str, version_id: int) -> int:
    response = alice.create_grant(client_id, version_id, expires_in(days=1))
    assert response.status_code == 201
    return response.json()["id"]


def sync(mock_lender: httpx.Client, client_id: str) -> None:
    """Have the lender check core, which is how it learns about new grants."""
    response = mock_lender.post(f"/api/lenders/{client_id}/sync")
    assert response.status_code == 200


def fetch(mock_lender: httpx.Client, client_id: str, grant_id: int) -> httpx.Response:
    return mock_lender.post(f"/api/lenders/{client_id}/grants/{grant_id}/fetch")


def copies(mock_lender: httpx.Client, client_id: str) -> dict[int, dict[str, Any]]:
    response = mock_lender.get(f"/api/lenders/{client_id}/copies")
    assert response.status_code == 200
    return {copy["grantId"]: copy for copy in response.json()}


def copy_xml(
    mock_lender: httpx.Client, client_id: str, grant_id: int
) -> httpx.Response:
    return mock_lender.get(f"/lenders/{client_id}/copies/{grant_id}/xml")


@pytest.mark.req("L-01")
def test_copy_outlives_revocation(
    alice: BorrowerClient, lender_a: LenderClient, mock_lender: httpx.Client
):
    version = alice.must_finalize(complete())
    xml = alice.version_xml(version["id"]).content
    grant = new_grant(alice, "lender-a", version["id"])
    sync(mock_lender, "lender-a")

    fetched = fetch(mock_lender, "lender-a", grant)
    assert fetched.status_code == 200
    assert fetched.json()["sha256"] == version["sha256"]
    assert copy_xml(mock_lender, "lender-a", grant).content == xml

    assert alice.revoke(grant).status_code == 200

    # Future fetches stop, for the lender's system and for a direct call to core.
    assert fetch(mock_lender, "lender-a", grant).status_code == 409
    assert reply(lender_a.fetch(grant)) == reply(lender_a.fetch(ABSENT_ID))

    # The copy it already had is still there, unchanged, even after it syncs.
    sync(mock_lender, "lender-a")
    assert copies(mock_lender, "lender-a")[grant]["sha256"] == version["sha256"]
    kept = copy_xml(mock_lender, "lender-a", grant)
    assert kept.status_code == 200
    assert kept.content == xml


@pytest.mark.req("L-01")
def test_revoking_before_any_fetch_leaves_no_copy(
    alice: BorrowerClient, mock_lender: httpx.Client
):
    """A lender holds only what it fetched, so the copy above isn't a given."""
    version = alice.must_finalize(complete())
    grant = new_grant(alice, "lender-a", version["id"])
    sync(mock_lender, "lender-a")

    assert alice.revoke(grant).status_code == 200

    assert fetch(mock_lender, "lender-a", grant).status_code == 409
    assert grant not in copies(mock_lender, "lender-a")
    assert copy_xml(mock_lender, "lender-a", grant).status_code == 404


@pytest.mark.req("FR-06", "L-01")
def test_revoking_one_lender_leaves_the_others_access_and_copy(
    alice: BorrowerClient, mock_lender: httpx.Client
):
    """The same as FR-06's direct test, through a lender's own system."""
    version = alice.must_finalize(complete())
    grant_a = new_grant(alice, "lender-a", version["id"])
    grant_b = new_grant(alice, "lender-b", version["id"])
    sync(mock_lender, "lender-a")
    sync(mock_lender, "lender-b")
    assert fetch(mock_lender, "lender-a", grant_a).status_code == 200

    assert alice.revoke(grant_a).status_code == 200

    assert fetch(mock_lender, "lender-a", grant_a).status_code == 409
    assert fetch(mock_lender, "lender-b", grant_b).status_code == 200
    assert grant_b in copies(mock_lender, "lender-b")
    assert grant_b not in copies(mock_lender, "lender-a")
