"""NFR-01, NFR-02, L-02: the SSN and HMDA data stay out of the prototype.

Names are compared word by word, because a substring search would flag harmless
names: "ssn" is in "businessName", and "race" is in "GracePeriod".

From outside, "stored" can only be shown through what core accepts and returns.
"""

import re
from collections.abc import Iterable
from typing import Any

import httpx
import pytest
from lxml import etree  # ty: ignore

from support.clients import BorrowerClient
from support.data import complete, drop_nulls, every_field
from support.xml import MISMO_NS, fetch_finalized

WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+")
SSN_WORDS = {"ssn", "itin", "tin", "taxpayer"}
HMDA_WORDS = {"hmda", "ethnicity", "race", "gender", "sex", "monitoring"}


def words(name: str) -> set[str]:
    """`TaxpayerIdentifierValue` -> {"taxpayer", "identifier", "value"}."""
    return {word.lower() for word in WORD.findall(name)}


def excluded(names: Iterable[str]) -> set[str]:
    return {name for name in names if words(name) & (SSN_WORDS | HMDA_WORDS)}


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


def disallowed_elements(doc: etree._Element) -> set[str]:
    """Elements for excluded data, and any extension or non-MISMO elements."""
    found = set()
    for element in doc.iter(etree.Element):
        name = etree.QName(element)
        if (
            name.namespace != MISMO_NS
            or "extension" in words(name.localname)
            or excluded([name.localname])
        ):
            found.add(element.tag)
    return found


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
