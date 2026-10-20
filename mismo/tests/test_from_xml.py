"""Unit tests for ``from_xml``: the round trip and the subset boundary.

``from_xml(to_xml(u)) == u`` for every shape of application (FR-04). XML
holding something the URLA subset cannot represent is rejected with
``UnsupportedError`` instead of being mapped to the nearest value (L-03,
L-04). Those cases are built by editing synthetic ``to_xml`` output, so they
run without the DU test cases; the DU test cases, when downloaded, are checked
as well.

These are unit tests; the black-box checks that verify requirements live in
eval/.
"""

from collections.abc import Callable
from copy import deepcopy
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


# Fannie Mae's DU test cases: gitignored, so skipped when not downloaded. Each
# uses something outside the subset, so each must be rejected by name.

DU_CASES = (
    Path(__file__).parents[1]
    / "schema/DU Specification Test Case Suite October 2026/Updated XML Files"
)
DU_REASONS = {
    "DI-C01": "AssetType",
    "DI-C02": "co-borrower",
    "DI-C03": "co-borrower",
    "DI-C04": "co-borrower",
    "DI-C05": "AssetType",
    "DI-C06": "co-borrower",
    "DI-C07": "AssetType",
    "DI-C08": "co-borrower",
    "DI-C09": "co-borrower",
    "DI-CL01": "self-employment",
    "DI-FHA01": "co-borrower",
    "DI-FHA02": "AssetType",
    "DI-FHA03": "BorrowerResidencyBasisType",
    "DI-FHA04": "co-borrower",
    "DI-VA01": "MortgageType",
    "DI-VA02": "co-borrower",
    "DI-VA03": "co-borrower",
    "DI-VA04": "co-borrower",
}
DU_FILES = sorted(DU_CASES.glob("*.xml"))


@pytest.mark.skipif(not DU_FILES, reason="DU test cases not downloaded")
@pytest.mark.parametrize(
    "path", DU_FILES or [None], ids=lambda p: p.name.split("_")[0] if p else "none"
)
def test_du_test_cases_are_rejected_by_name(path: Path) -> None:
    with pytest.raises(UnsupportedError, match=DU_REASONS[path.name.split("_")[0]]):
        from_xml(path.read_bytes())
