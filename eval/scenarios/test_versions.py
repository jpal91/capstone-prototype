import hashlib

import pytest

from support.clients import BorrowerClient
from support.data import complete


@pytest.mark.req("FR-02")
def test_finalize_is_immutable(alice: BorrowerClient):
    # v1's hash is taken here, before v2 exists, so it pins v1's original bytes.
    v1 = alice.must_finalize(complete())
    v2 = alice.must_finalize(complete(borrower={"dateOfBirth": "1989-03-14"}))

    assert v2["sha256"] != v1["sha256"]
    assert v2["number"] == v1["number"] + 1

    for version in (v1, v2):
        xml = alice.version_xml(version["id"])

        assert xml.status_code == 200
        assert xml.headers["X-Content-SHA256"] == version["sha256"]
        assert hashlib.sha256(xml.content).hexdigest() == version["sha256"]

    listed = alice.get("/versions")
    assert listed.status_code == 200

    by_id = {version["id"]: version for version in listed.json()}
    assert by_id[v1["id"]] == v1
