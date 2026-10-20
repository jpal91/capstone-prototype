"""Unit tests for ``from_xml``: the round trip and the subset boundary.

``from_xml(to_xml(u)) == u`` for every shape of application (FR-04). XML
holding something the URLA subset cannot represent is rejected with
``UnsupportedError`` instead of being mapped to the nearest value (L-03,
L-04). Those cases are built by editing synthetic ``to_xml`` output, so they
run without the DU test cases. When the DU test cases are downloaded, DI-C01
must be read and every other case rejected cleanly.

These are unit tests; the black-box checks that verify requirements live in
eval/.
"""

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree  # ty: ignore
from synthetic import FULL, application

from mismo.convert import from_xml, to_xml
from mismo.convert.from_xml import MissingError, UnsupportedError
from mismo.urla import Urla

MISMO = "{http://www.mismo.org/residential/2009/schemas}"


def edited(urla: Urla, edit: Callable[[etree._Element], None]) -> bytes:
    """``to_xml`` output for ``urla`` after ``edit`` changes the tree."""
    doc = etree.fromstring(to_xml(urla))
    edit(doc)
    return etree.tostring(doc)


def first(doc: etree._Element, name: str) -> etree._Element:
    found = doc.find(f".//{MISMO}{name}")
    assert found is not None, f"no {name} in the to_xml output"
    return found


def set_text(name: str, text: str) -> Callable[[etree._Element], None]:
    def edit(doc: etree._Element) -> None:
        first(doc, name).text = text

    return edit


def remove(name: str) -> Callable[[etree._Element], None]:
    def edit(doc: etree._Element) -> None:
        found = first(doc, name)
        found.getparent().remove(found)

    return edit


# Round trip (FR-04)


@pytest.mark.parametrize(("assets", "liabilities"), [(0, 0), (1, 0), (0, 1), (3, 2)])
def test_round_trip(assets: int, liabilities: int) -> None:
    urla = application(assets, liabilities)
    assert from_xml(to_xml(urla)) == urla


def test_round_trip_with_every_field() -> None:
    assert from_xml(to_xml(FULL)) == FULL


def test_present_housing_expenses_are_ignored() -> None:
    # The borrower's current housing costs share HOUSING_EXPENSES with the
    # proposed ones for the subject property.
    xml = edited(FULL, set_text("HousingExpenseTimingType", "Present"))
    assert from_xml(xml).subject_property.monthly_hoi is None


def test_property_value_falls_back_to_the_sales_contract() -> None:
    # A purchase without an appraisal yet (e.g., DU test case DI-FHA03).
    urla = application(0, 0)
    xml = edited(urla, remove("PROPERTY_VALUATIONS"))
    assert from_xml(xml) == urla


# The subset boundary (L-03, L-04)


def self_employed(doc: etree._Element) -> None:
    """Report income as a 25%-or-more owner does: on the employer (L-04)."""
    current_income = first(doc, "CURRENT_INCOME")
    current_income.getparent().remove(current_income)
    amount = etree.Element(f"{MISMO}EmploymentMonthlyIncomeAmount")
    amount.text = "8000.00"
    first(doc, "EmploymentStartDate").addprevious(amount)


def owned_real_estate(doc: etree._Element) -> None:
    """Replace the first asset's details with a property it owns (URLA 3)."""
    detail = first(doc, "ASSET_DETAIL")
    detail.addprevious(etree.Element(f"{MISMO}OWNED_PROPERTY"))
    detail.getparent().remove(detail)


def co_borrower(doc: etree._Element) -> None:
    """Add a second borrower: a copy of the first PARTY (L-03)."""
    party = first(doc, "PARTY")
    party.addnext(deepcopy(party))


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (set_text("AssetType", "GiftOfCash"), "AssetType"),
        (set_text("LiabilityType", "Taxes"), "LiabilityType"),
        (set_text("MortgageType", "VA"), "MortgageType"),
        (set_text("LoanPurposeType", "MortgageModification"), "LoanPurposeType"),
        (set_text("PropertyUsageType", "Other"), "PropertyUsageType"),
        (
            set_text("BorrowerResidencyBasisType", "LivingRentFree"),
            "BorrowerResidencyBasisType",
        ),
        (set_text("IncomeType", "Pension"), "IncomeType"),
        (self_employed, "self-employment"),
        (owned_real_estate, "owned real estate"),
        (co_borrower, "co-borrower"),
    ],
    ids=[
        "asset",
        "liability",
        "mortgage",
        "purpose",
        "occupancy",
        "residency",
        "income-type",
        "self-employed",
        "owned-property",
        "co-borrower",
    ],
)
def test_values_outside_the_subset_are_rejected(
    edit: Callable[[etree._Element], None], message: str
) -> None:
    xml = edited(application(1, 1), edit)
    with pytest.raises(UnsupportedError, match=message):
        from_xml(xml)


@pytest.mark.parametrize("name", ["FirstName", "BorrowerBirthDate", "BaseLoanAmount"])
def test_missing_required_elements_are_named(name: str) -> None:
    xml = edited(application(0, 0), remove(name))
    with pytest.raises(MissingError):
        from_xml(xml)


# Fannie Mae's DU test cases: gitignored, so skipped when not downloaded.
# DI-C01 is within the subset apart from extra income items; every other case
# uses something outside it.

DU_CASES = (
    Path(__file__).parents[1]
    / "schema/DU Specification Test Case Suite October 2026/Updated XML Files"
)
DU_FILES = {p.name.split("_")[0]: p for p in sorted(DU_CASES.glob("*.xml"))}
NS = {"m": MISMO[1:-1]}

needs_du = pytest.mark.skipif(not DU_FILES, reason="DU test cases not downloaded")


def amounts(doc: etree._Element, path: str) -> list[Decimal]:
    return [Decimal(e.text) for e in doc.iterfind(path, NS)]


@needs_du
def test_du_c01_is_read() -> None:
    # Expected values are read from the file itself, so none are copied here.
    raw = DU_FILES["DI-C01"].read_bytes()
    doc = etree.fromstring(raw)
    urla = from_xml(raw)

    assert urla.borrower.first_name == doc.findtext(".//m:NAME/m:FirstName", None, NS)
    assert urla.loan.loan_amount == Decimal(
        doc.findtext(".//m:BaseLoanAmount", None, NS)
    )
    assert [a.amount for a in urla.assets] == amounts(
        doc, ".//m:ASSET_DETAIL/m:AssetCashOrMarketValueAmount"
    )
    assert [l.balance for l in urla.liabilities] == amounts(
        doc, ".//m:LIABILITY_DETAIL/m:LiabilityUnpaidBalanceAmount"
    )

    proposed = {
        e.findtext("m:HousingExpenseType", None, NS): Decimal(
            e.findtext("m:HousingExpensePaymentAmount", None, NS)
        )
        for e in doc.iterfind(".//m:HOUSING_EXPENSE", NS)
        if e.findtext("m:HousingExpenseTimingType", None, NS) == "Proposed"
    }
    assert urla.subject_property.monthly_hoi == proposed["HomeownersInsurance"]
    assert urla.subject_property.monthly_taxes == proposed["RealEstateTax"]

    # Only base pay is imported; C01's other income items are ignored (L-04).
    items = list(doc.iterfind(".//m:CURRENT_INCOME_ITEM_DETAIL", NS))
    base = [i for i in items if i.findtext("m:IncomeType", None, NS) == "Base"]
    assert len(base) == 1 < len(items)
    assert urla.income.monthly_income == Decimal(
        base[0].findtext("m:CurrentIncomeMonthlyTotalAmount", None, NS)
    )


@needs_du
def test_du_c01_leaves_its_ssn_and_hmda_data_behind() -> None:
    # C01 is a full application; what comes back out is a pre-application
    # (NFR-01, NFR-02) that round-trips like any other.
    raw = DU_FILES["DI-C01"].read_bytes()
    urla = from_xml(raw)
    xml = to_xml(urla)

    assert b"TaxpayerIdentifier" in raw and b"HMDA" in raw
    assert b"TaxpayerIdentifier" not in xml and b"HMDA" not in xml
    assert from_xml(xml) == urla


@needs_du
@pytest.mark.parametrize("name", [n for n in DU_FILES if n != "DI-C01"] or ["none"])
def test_other_du_cases_are_rejected_cleanly(name: str) -> None:
    # Each uses something outside the subset. Any other error (MissingError,
    # TypeError, ...) would mean a path assumption failed on real-world XML.
    with pytest.raises(UnsupportedError):
        from_xml(DU_FILES[name].read_bytes())
