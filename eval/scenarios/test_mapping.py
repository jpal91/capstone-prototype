"""FR-04: draft values appear at their MISMO paths in the XML a borrower gets.

The paths are written out here rather than read from the mismo library, so the
mapper isn't checking itself. mismo's own tests cover the full from_xml round
trip; this reads the XML that came through core's API.
"""

from typing import Any

import pytest
from lxml import etree  # ty: ignore

from support.clients import BorrowerClient
from support.data import complete, every_field
from support.xml import NAMESPACES, fetch_finalized

BORROWER = "//m:PARTY/m:ROLES/m:ROLE/m:BORROWER"
NAME = "//m:PARTY/m:INDIVIDUAL/m:NAME"
CONTACTS = "//m:PARTY/m:INDIVIDUAL/m:CONTACT_POINTS/m:CONTACT_POINT"
RESIDENCE = f"{BORROWER}/m:RESIDENCES/m:RESIDENCE"
EMPLOYER = f"{BORROWER}/m:EMPLOYERS/m:EMPLOYER"
INCOME = (
    f"{BORROWER}/m:CURRENT_INCOME/m:CURRENT_INCOME_ITEMS/m:CURRENT_INCOME_ITEM"
    "/m:CURRENT_INCOME_ITEM_DETAIL"
)
SUBJECT = "//m:COLLATERALS/m:COLLATERAL/m:SUBJECT_PROPERTY"
LOAN = "//m:LOANS/m:LOAN"
EXPENSE = f"{LOAN}/m:HOUSING_EXPENSES/m:HOUSING_EXPENSE"

# Field path in the draft -> where its value should be in the XML. XPath counts
# rows from 1, so a mapper that reorders asset or liability rows fails.
FIELDS = {
    "borrower.firstName": f"{NAME}/m:FirstName",
    "borrower.lastName": f"{NAME}/m:LastName",
    "borrower.dateOfBirth": f"{BORROWER}/m:BORROWER_DETAIL/m:BorrowerBirthDate",
    "borrower.phoneNumber": (
        f"{CONTACTS}/m:CONTACT_POINT_TELEPHONE/m:ContactPointTelephoneValue"
    ),
    "borrower.email": f"{CONTACTS}/m:CONTACT_POINT_EMAIL/m:ContactPointEmailValue",
    "address.streetAddress": f"{RESIDENCE}/m:ADDRESS/m:AddressLineText",
    "address.city": f"{RESIDENCE}/m:ADDRESS/m:CityName",
    "address.state": f"{RESIDENCE}/m:ADDRESS/m:StateCode",
    "address.zipCode": f"{RESIDENCE}/m:ADDRESS/m:PostalCode",
    "address.ownStatus": f"{RESIDENCE}/m:RESIDENCE_DETAIL/m:BorrowerResidencyBasisType",
    "address.monthsAtAddress": (
        f"{RESIDENCE}/m:RESIDENCE_DETAIL/m:BorrowerResidencyDurationMonthsCount"
    ),
    "subjectProperty.streetAddress": f"{SUBJECT}/m:ADDRESS/m:AddressLineText",
    "subjectProperty.city": f"{SUBJECT}/m:ADDRESS/m:CityName",
    "subjectProperty.state": f"{SUBJECT}/m:ADDRESS/m:StateCode",
    "subjectProperty.zipCode": f"{SUBJECT}/m:ADDRESS/m:PostalCode",
    "subjectProperty.monthlyTaxes": (
        f"{EXPENSE}[m:HousingExpenseType='RealEstateTax']/m:HousingExpensePaymentAmount"
    ),
    "subjectProperty.monthlyHoi": (
        f"{EXPENSE}[m:HousingExpenseType='HomeownersInsurance']"
        "/m:HousingExpensePaymentAmount"
    ),
    "subjectProperty.propertyValue": (
        f"{SUBJECT}/m:PROPERTY_VALUATIONS/m:PROPERTY_VALUATION"
        "/m:PROPERTY_VALUATION_DETAIL/m:PropertyValuationAmount"
    ),
    "subjectProperty.occupancy": f"{SUBJECT}/m:PROPERTY_DETAIL/m:PropertyUsageType",
    "income.employerName": (
        f"{EMPLOYER}/m:LEGAL_ENTITY/m:LEGAL_ENTITY_DETAIL/m:FullName"
    ),
    "income.monthlyIncome": f"{INCOME}/m:CurrentIncomeMonthlyTotalAmount",
    "income.startDate": f"{EMPLOYER}/m:EMPLOYMENT/m:EmploymentStartDate",
    "income.position": f"{EMPLOYER}/m:EMPLOYMENT/m:EmploymentPositionDescription",
    "loan.loanTermMonths": (
        f"{LOAN}/m:AMORTIZATION/m:AMORTIZATION_RULE/m:LoanAmortizationPeriodCount"
    ),
    "loan.loanProgram": f"{LOAN}/m:TERMS_OF_LOAN/m:MortgageType",
    "loan.loanAmount": f"{LOAN}/m:TERMS_OF_LOAN/m:BaseLoanAmount",
    "loan.loanPurpose": f"{LOAN}/m:TERMS_OF_LOAN/m:LoanPurposeType",
}

for row in (0, 1):
    asset = f"//m:ASSETS/m:ASSET[{row + 1}]"
    liability = f"//m:LIABILITIES/m:LIABILITY[{row + 1}]"
    detail = f"{liability}/m:LIABILITY_DETAIL"
    FIELDS |= {
        f"assets.{row}.institutionName": f"{asset}/m:ASSET_HOLDER/m:NAME/m:FullName",
        f"assets.{row}.assetType": f"{asset}/m:ASSET_DETAIL/m:AssetType",
        f"assets.{row}.amount": (
            f"{asset}/m:ASSET_DETAIL/m:AssetCashOrMarketValueAmount"
        ),
        f"liabilities.{row}.institutionName": (
            f"{liability}/m:LIABILITY_HOLDER/m:NAME/m:FullName"
        ),
        f"liabilities.{row}.liabilityType": f"{detail}/m:LiabilityType",
        f"liabilities.{row}.monthlyAmount": f"{detail}/m:LiabilityMonthlyPaymentAmount",
        f"liabilities.{row}.balance": f"{detail}/m:LiabilityUnpaidBalanceAmount",
    }
FIELDS["liabilities.1.monthsRemaining"] = (
    "//m:LIABILITIES/m:LIABILITY[2]/m:LIABILITY_DETAIL"
    "/m:LiabilityRemainingTermMonthsCount"
)

# Where MISMO's spelling differs from the draft's on purpose.
TRANSLATED = {
    "borrower.phoneNumber": "5205550123",
    "assets.0.assetType": "CheckingAccount",
    "assets.1.assetType": "SavingsAccount",
}


def draft_fields(value: Any, path: str = "") -> dict[str, Any]:
    """Flatten a draft: {"borrower": {"email": "x"}} -> {"borrower.email": "x"}."""
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return {path: value}

    fields: dict[str, Any] = {}
    for key, item in items:
        fields |= draft_fields(item, f"{path}.{key}" if path else str(key))
    return fields


def only_text(doc: etree._Element, xpath: str) -> str:
    """The text at `xpath`, which has to match exactly one element."""
    found = doc.xpath(xpath, namespaces=NAMESPACES)
    assert len(found) == 1, f"{len(found)} matches for {xpath}"
    return found[0].text


@pytest.fixture(scope="module")
def emitted(alice: BorrowerClient) -> etree._Element:
    """One finalized version of every_field(), shared by this module's checks."""
    return fetch_finalized(alice, every_field())


@pytest.mark.req("FR-04")
@pytest.mark.parametrize("field", FIELDS)
def test_field_reaches_its_mismo_path(emitted: etree._Element, field: str):
    sent = draft_fields(every_field())[field]
    expected = TRANSLATED.get(field, str(sent))

    assert only_text(emitted, FIELDS[field]) == expected


@pytest.mark.req("FR-04")
def test_every_draft_field_has_a_path():
    """A field added to every_field() can't go unchecked."""
    assert set(draft_fields(every_field())) == set(FIELDS)


@pytest.mark.req("FR-04")
def test_purchase_draft_reaches_its_mismo_paths(alice: BorrowerClient):
    """complete() takes the purchase branch, which every_field() doesn't."""
    draft = complete()
    doc = fetch_finalized(alice, draft)
    property_value = draft["subjectProperty"]["propertyValue"]
    sales_contract = (
        f"{SUBJECT}/m:SALES_CONTRACTS/m:SALES_CONTRACT"
        "/m:SALES_CONTRACT_DETAIL/m:SalesContractAmount"
    )

    assert only_text(doc, FIELDS["loan.loanPurpose"]) == "Purchase"
    assert only_text(doc, FIELDS["loan.loanProgram"]) == "Conventional"
    assert only_text(doc, FIELDS["subjectProperty.occupancy"]) == "PrimaryResidence"
    assert only_text(doc, sales_contract) == property_value
