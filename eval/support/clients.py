"""HTTP clients for each party, as each would reach the services.

Methods return the raw response: the scenarios assert on status codes and
bodies themselves, so a check never hides inside a helper. `must_*` helpers
are for setup steps that have to succeed before a scenario can start.
"""

import time
from typing import Any

import httpx

from support.data import expires_in
from support.settings import LENDERS

# Finalize maps and validates against the DU schema; give it room.
TIMEOUT = httpx.Timeout(30.0)


def core_client(base_url: str) -> httpx.Client:
    """A client with no credentials at all."""
    return httpx.Client(base_url=base_url, timeout=TIMEOUT)


class BorrowerClient(httpx.Client):
    """A borrower's session with core (Bearer token from /auth/login)."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        super().__init__(base_url=base_url, timeout=TIMEOUT)
        self.username = username
        response = self.post(
            "/auth/login", json={"username": username, "password": password}
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"login as {username} failed: {response.status_code} {response.text}"
            )
        self.headers["Authorization"] = f"Bearer {response.json()['token']}"

    def put_draft(self, draft: dict[str, Any]) -> httpx.Response:
        return self.put("/draft", json=draft)

    def finalize(self) -> httpx.Response:
        return self.post("/draft/finalize")

    def version_xml(self, version_id: int) -> httpx.Response:
        return self.get(f"/versions/{version_id}/xml")

    def lender_id(self, client_id: str) -> int:
        """core's numeric ID for a lender, which POST /grants takes.

        Borrowers see lenders by name only, so match on the seeded name.
        """
        name, _ = LENDERS[client_id]
        response = self.get("/lenders")
        response.raise_for_status()
        for lender in response.json():
            if lender["name"] == name:
                return lender["id"]
        raise LookupError(f"core has no lender named {name}")

    def create_grant(
        self, client_id: str, version_id: int, expires_at: str
    ) -> httpx.Response:
        return self.post(
            "/grants",
            json={
                "lenderId": self.lender_id(client_id),
                "versionId": version_id,
                "expiresAt": expires_at,
            },
        )

    def revoke(self, grant_id: int) -> httpx.Response:
        return self.post(f"/grants/{grant_id}/revoke")

    def must_finalize(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Save `draft` and finalize it; returns the new version."""
        saved = self.put_draft(draft)
        if saved.status_code != 204:
            raise RuntimeError(f"PUT /draft: {saved.status_code} {saved.text}")
        version = self.finalize()
        if version.status_code != 201:
            raise RuntimeError(
                f"POST /draft/finalize: {version.status_code} {version.text}"
            )
        return version.json()

    def must_grant(self, client_id: str, version_id: int, **delta: float) -> int:
        """Create a grant expiring after `delta` (days=1); returns its ID."""
        response = self.create_grant(client_id, version_id, expires_in(**delta))
        if response.status_code != 201:
            raise RuntimeError(f"POST /grants: {response.status_code} {response.text}")
        return response.json()["id"]

    def view_grant(self, grant_id: int) -> dict[str, Any]:
        """The grant as this borrower sees it in GET /grants."""
        response = self.get("/grants")
        response.raise_for_status()
        return {grant["id"]: grant for grant in response.json()}[grant_id]

    def wait_until_expired(self, grant_id: int) -> None:
        deadline = time.monotonic() + 10
        while self.view_grant(grant_id)["status"] != "expired":
            if time.monotonic() > deadline:
                raise RuntimeError(f"grant {grant_id} never expired")
            time.sleep(0.1)


class LenderClient(httpx.Client):
    """A lender calling core's lender API with its own credentials (HTTP Basic)."""

    def __init__(self, base_url: str, client_id: str, secret: str) -> None:
        super().__init__(base_url=base_url, auth=(client_id, secret), timeout=TIMEOUT)
        self.client_id = client_id

    def grants(self) -> httpx.Response:
        return self.get("/lender/grants")

    def fetch(self, grant_id: int) -> httpx.Response:
        return self.get(f"/lender/grants/{grant_id}/application")


def reply(response: httpx.Response) -> tuple[int, bytes, dict[str, str]]:
    """Everything a lender can see, except the time it was sent."""
    headers = {k: v for k, v in response.headers.items() if k != "date"}
    return response.status_code, response.content, headers


def mock_lender_client(base_url: str) -> httpx.Client:
    """The mock lender's JSON routes (/api/lenders/{clientId}/...)."""
    return httpx.Client(base_url=base_url, timeout=TIMEOUT)
