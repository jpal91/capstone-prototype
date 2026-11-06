import pytest

from support.clients import BorrowerClient
from support.data import complete, drop_nulls


@pytest.mark.req("FR-01")
def test_saves_and_reads_back_draft(alice: BorrowerClient):
    draft = complete()

    assert alice.put_draft(draft).status_code == 204

    response = alice.get("/draft")
    assert response.status_code == 200
    assert drop_nulls(response.json()) == draft


@pytest.mark.req("FR-01")
def test_edit_replaces_saved_value(alice: BorrowerClient):
    draft = complete()
    edited = complete(borrower={"dateOfBirth": "1989-03-14"})
    edited["assets"] = []

    assert alice.put_draft(draft).status_code == 204
    assert alice.put_draft(edited).status_code == 204

    response = alice.get("/draft")
    assert response.status_code == 200
    assert drop_nulls(response.json()) == edited
