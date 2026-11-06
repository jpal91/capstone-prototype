"""NFR-01, NFR-02, L-02: the SSN and HMDA data stay out of the prototype.

"Stored" is the one claim that needs core's database: the last three tests read it.
"""

from typing import Any

import httpx
import psycopg
import pytest
from lxml import etree  # ty: ignore

from support.clients import BorrowerClient
from support.data import complete, drop_nulls, every_field
from support.exclusions import disallowed_elements, excluded
from support.xml import MISMO_NS, PARSER, fetch_finalized


def json_keys(value: Any) -> set[str]:
    """Every key at any depth of a stored JSON value."""
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            keys |= json_keys(item)
    return keys


def property_names(schema: Any) -> set[str]:
    """Every property name anywhere in an OpenAPI document."""
    names: set[str] = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                names.update(value)
            names |= property_names(value)
    elif isinstance(schema, list):
        for item in schema:
            names |= property_names(item)
    return names


@pytest.fixture(scope="module")
def emitted(alice: BorrowerClient) -> etree._Element:
    return fetch_finalized(alice, every_field())


@pytest.mark.parametrize(
    ("section", "field"),
    [
        pytest.param(None, "ssn", marks=pytest.mark.req("NFR-01")),
        pytest.param("borrower", "ssn", marks=pytest.mark.req("NFR-01")),
        pytest.param("borrower", "taxpayerId", marks=pytest.mark.req("NFR-01")),
        pytest.param("borrower", "race", marks=pytest.mark.req("NFR-02")),
        pytest.param("borrower", "ethnicity", marks=pytest.mark.req("NFR-02")),
        pytest.param("borrower", "sex", marks=pytest.mark.req("NFR-02")),
    ],
)
def test_draft_rejects_excluded_field(
    alice: BorrowerClient, section: str | None, field: str
):
    saved = complete()
    assert alice.put_draft(saved).status_code == 204

    attempt = complete()
    (attempt[section] if section else attempt)[field] = "sample"
    response = alice.put_draft(attempt)

    assert response.status_code == 422
    loc = ["body", section, field] if section else ["body", field]
    assert [(e["type"], e["loc"]) for e in response.json()["detail"]] == [
        ("extra_forbidden", loc)
    ]
    assert drop_nulls(alice.get("/draft").json()) == saved


@pytest.mark.req("NFR-01", "NFR-02")
def test_api_schema_has_no_excluded_fields(anon: httpx.Client):
    response = anon.get("/openapi.json")
    assert response.status_code == 200

    names = property_names(response.json())

    assert "dateOfBirth" in names  # it did read the draft's fields
    assert excluded(names) == set()


@pytest.mark.req("NFR-01", "NFR-02", "L-02")
def test_emitted_xml_has_no_disallowed_elements(emitted: etree._Element):
    assert disallowed_elements(emitted) == set()


@pytest.mark.parametrize(
    "tag",
    [
        pytest.param(
            f"{{{MISMO_NS}}}TaxpayerIdentifierValue", marks=pytest.mark.req("NFR-01")
        ),
        pytest.param(
            f"{{{MISMO_NS}}}HMDAEthnicityType", marks=pytest.mark.req("NFR-02")
        ),
        pytest.param(
            f"{{{MISMO_NS}}}GOVERNMENT_MONITORING", marks=pytest.mark.req("NFR-02")
        ),
        pytest.param(f"{{{MISMO_NS}}}EXTENSION", marks=pytest.mark.req("L-02")),
        pytest.param("{urn:example:other}LoanData", marks=pytest.mark.req("L-02")),
    ],
)
def test_xml_check_finds_planted_element(emitted: etree._Element, tag: str):
    """Without this, a check that never finds anything would also pass."""
    doc = etree.fromstring(etree.tostring(emitted))
    etree.SubElement(doc, tag)

    assert disallowed_elements(doc) == {tag}


@pytest.mark.req("NFR-01", "NFR-02")
def test_core_tables_have_no_excluded_columns(db: psycopg.Connection):
    rows = db.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = 'public'"
    ).fetchall()
    names = {row["column_name"] for row in rows}

    assert "expires_at" in names  # it did read core's tables
    assert excluded(names) == set()


@pytest.mark.req("NFR-01", "NFR-02")
def test_stored_drafts_have_no_excluded_fields(
    alice: BorrowerClient, db: psycopg.Connection
):
    assert alice.put_draft(every_field()).status_code == 204

    keys = set()
    for row in db.execute("SELECT data FROM draft").fetchall():
        keys |= json_keys(row["data"])

    assert "dateOfBirth" in keys  # it did read the draft's fields
    assert excluded(keys) == set()


@pytest.mark.req("NFR-01", "NFR-02")
def test_stored_versions_have_no_disallowed_elements(
    db: psycopg.Connection, emitted: etree._Element
):
    rows = db.execute("SELECT xml FROM version").fetchall()

    assert rows  # `emitted` finalized one
    for row in rows:
        doc = etree.fromstring(bytes(row["xml"]), PARSER)
        assert disallowed_elements(doc) == set()
