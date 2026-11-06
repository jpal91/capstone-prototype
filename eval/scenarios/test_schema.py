import pytest
from lxml import etree  # ty: ignore

from support.clients import BorrowerClient
from support.data import complete, every_field
from support.xml import MISMO, fetch_finalized


@pytest.mark.req("FR-03")
@pytest.mark.parametrize(
    "draft",
    [complete(), every_field()],
    ids=["required-fields", "every-field"],
)
def test_finalized_version_validates(
    alice: BorrowerClient, du_schema: etree.XMLSchema, draft: dict
):
    doc = fetch_finalized(alice, draft)

    assert du_schema.validate(doc), du_schema.error_log


@pytest.mark.req("FR-03")
def test_schema_check_rejects_invalid_xml(
    alice: BorrowerClient, du_schema: etree.XMLSchema
):
    """Without this, a validator that accepts anything would also pass."""
    doc = fetch_finalized(alice, complete())
    assert du_schema.validate(doc), du_schema.error_log

    doc.find(f".//{MISMO}BaseLoanAmount").text = "not-a-number"

    assert not du_schema.validate(doc)
    assert "BaseLoanAmount" in str(du_schema.error_log)
