"""Unit tests for the URLA draft and finalized models.

Comments name the requirement each group supports (see docs/requirements.md).
These are unit tests; the black-box checks that verify requirements live in
eval/.
"""

import copy
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from mismo.urla import Urla, UrlaDraft

# Synthetic data only (NFR-06).
COMPLETE = {
    "borrower": {
        "firstName": "Alex",
        "lastName": "Example",
        "dateOfBirth": "1990-01-01",
        "phoneNumber": "202-555-0123",
        "email": "alex@example.com",
    },
    "address": {
        "streetAddress": "100 Example Ave",
        "city": "Tucson",
        "state": "AZ",
        "zipCode": "85701",
        "ownStatus": "Rent",
        "monthsAtAddress": 24,
    },
    "subjectProperty": {
        "propertyValue": "350000.00",
        "occupancy": "PrimaryResidence",
    },
    "income": {
        "employerName": "Example Corp",
        "monthlyIncome": "6000.00",
        "startDate": "2020-05-01",
        "position": "Analyst",
    },
    "assets": [
        {
            "institutionName": "Example Bank",
            "assetType": "Checking",
            "amount": "20000.00",
        }
    ],
    "liabilities": [
        {
            "institutionName": "Example Card",
            "liabilityType": "Revolving",
            "monthlyAmount": "50.00",
            "balance": "1200.00",
        }
    ],
    "loan": {
        "loanTermMonths": 360,
        "loanProgram": "Conventional",
        "loanAmount": "280000.00",
        "loanPurpose": "Purchase",
    },
}

SUBJECT_ADDRESS = {
    "streetAddress": "200 Example St",
    "city": "Tucson",
    "state": "AZ",
    "zipCode": "85702",
}


def complete(**changes: dict) -> dict:
    """A copy of COMPLETE with the given sections updated."""
    payload: dict[str, Any] = copy.deepcopy(COMPLETE)
    for section, values in changes.items():
        payload[section].update(values)
    return payload


def finalize(payload: dict) -> Urla:
    """Save as a draft, then validate as finalize will."""
    draft = UrlaDraft.model_validate(payload)
    return Urla.model_validate(draft.model_dump(by_alias=True, exclude_none=True))


def error_locs(exc: pytest.ExceptionInfo[ValidationError]) -> set[tuple]:
    return {e["loc"] for e in exc.value.errors()}


# --- Drafts (FR-01) ----------------------------------------------------------


def test_empty_draft_saves():
    assert UrlaDraft.model_validate({}) == UrlaDraft()


def test_partial_draft_saves():
    draft = UrlaDraft.model_validate({"address": {"city": "Tucson"}})
    assert draft.address.city == "Tucson"
    assert draft.borrower.first_name is None


def test_camel_case_keys_accepted_at_every_level():
    draft = UrlaDraft.model_validate(COMPLETE)
    assert draft.borrower.first_name == "Alex"
    assert draft.address.months_at_address == 24
    assert draft.subject_property.property_value == Decimal("350000.00")
    assert draft.income.employer_name == "Example Corp"
    assert draft.assets[0].institution_name == "Example Bank"
    assert draft.liabilities[0].monthly_amount == Decimal("50.00")
    assert draft.loan.loan_term_months == 360


def test_snake_case_keys_accepted():
    draft = UrlaDraft.model_validate({"borrower": {"first_name": "Alex"}})
    assert draft.borrower.first_name == "Alex"


def test_output_is_camel_case_at_every_level():
    dumped = UrlaDraft.model_validate(COMPLETE).model_dump(by_alias=True)
    assert "firstName" in dumped["borrower"]
    assert "monthsAtAddress" in dumped["address"]
    assert "propertyValue" in dumped["subjectProperty"]
    assert "institutionName" in dumped["assets"][0]
    assert "loanTermMonths" in dumped["loan"]


def test_draft_still_validates_values():
    with pytest.raises(ValidationError) as exc:
        UrlaDraft.model_validate({"loan": {"loanAmount": "-1"}})
    assert error_locs(exc) == {("loan", "loanAmount")}


# --- Fields that are never collected (NFR-01, NFR-02) ------------------------

# Every place a key could be sent: the top level, each section, and list items.
SECTIONS = [
    (),
    ("borrower",),
    ("address",),
    ("subjectProperty",),
    ("income",),
    ("loan",),
    ("assets", 0),
    ("liabilities", 0),
]
# SSN / taxpayer identifier, HMDA demographics (URLA section 8), and an
# account number, which is also deliberately left out.
FORBIDDEN_KEYS = [
    "ssn",
    "socialSecurityNumber",
    "taxpayerIdentifier",
    "ethnicity",
    "race",
    "sex",
    "accountNumber",
]


def put(payload: dict, path: tuple, key: str, value: str) -> None:
    target = payload
    for step in path:
        target = target[step]
    target[key] = value


@pytest.mark.parametrize("path", SECTIONS)
@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
@pytest.mark.parametrize("model", [UrlaDraft, Urla])
def test_uncollected_field_rejected(model, key, path):
    payload = copy.deepcopy(COMPLETE)
    put(payload, path, key, "000-00-0000")
    with pytest.raises(ValidationError) as exc:
        model.model_validate(payload)
    assert error_locs(exc) == {(*path, key)}
    assert exc.value.errors()[0]["type"] == "extra_forbidden"


def field_names(schema: dict) -> set[str]:
    """Every property name in a JSON schema, including nested definitions."""
    names = set(schema.get("properties", {}))
    for definition in schema.get("$defs", {}).values():
        names |= set(definition.get("properties", {}))
    return names


@pytest.mark.parametrize("model", [UrlaDraft, Urla])
def test_schema_has_no_uncollected_fields(model):
    names = {n.lower() for n in field_names(model.model_json_schema())}
    assert "firstname" in names  # the walk reaches nested models
    for word in ["ssn", "social", "taxpayer", "ethnicity", "race", "sex", "account"]:
        assert not any(word in n for n in names), word


# --- Field validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw", ["202-555-0123", "(202) 555-0123", "2025550123", "+1 202 555 0123"]
)
def test_phone_normalized_to_e164(raw):
    draft = UrlaDraft.model_validate({"borrower": {"phoneNumber": raw}})
    assert draft.borrower.phone_number == "+12025550123"


@pytest.mark.parametrize("raw", ["555-0123", "123-456-7890", "not a phone"])
def test_invalid_phone_rejected(raw):
    with pytest.raises(ValidationError):
        UrlaDraft.model_validate({"borrower": {"phoneNumber": raw}})


@pytest.mark.parametrize("zip_code", ["85701", "85701-1234"])
def test_valid_zip(zip_code):
    UrlaDraft.model_validate({"address": {"zipCode": zip_code}})


@pytest.mark.parametrize("zip_code", ["8570", "857011", "abcde", "857011234"])
def test_invalid_zip(zip_code):
    with pytest.raises(ValidationError):
        UrlaDraft.model_validate({"address": {"zipCode": zip_code}})


@pytest.mark.parametrize("state", ["az", "A", "ARZ"])
def test_invalid_state(state):
    with pytest.raises(ValidationError):
        UrlaDraft.model_validate({"address": {"state": state}})


def test_money_limited_to_cents():
    with pytest.raises(ValidationError):
        UrlaDraft.model_validate({"income": {"monthlyIncome": "6000.001"}})


# --- Finalizing (FR-02 input) -------------------------------------------------


def test_complete_purchase_without_property_address_finalizes():
    urla = finalize(COMPLETE)
    assert urla.subject_property.has_address is False


def test_finalize_keeps_values():
    urla = finalize(COMPLETE)
    draft = UrlaDraft.model_validate(COMPLETE)
    assert urla.model_dump(exclude_none=True) == draft.model_dump(exclude_none=True)


def test_empty_draft_reports_missing_fields():
    with pytest.raises(ValidationError) as exc:
        finalize({})
    errors = exc.value.errors()
    assert all(e["type"] == "missing" for e in errors)
    locs = {e["loc"] for e in errors}
    assert ("borrower", "firstName") in locs
    assert ("loan", "loanPurpose") in locs
    assert ("subjectProperty", "propertyValue") in locs


def test_empty_asset_and_liability_lists_allowed():
    payload = copy.deepcopy(COMPLETE)
    payload["assets"] = []
    payload["liabilities"] = []
    finalize(payload)


def test_optional_fields_may_be_missing():
    payload: dict[str, Any] = copy.deepcopy(COMPLETE)
    del payload["borrower"]["phoneNumber"]
    del payload["borrower"]["email"]
    del payload["income"]["position"]
    finalize(payload)


def test_future_dates_rejected():
    with pytest.raises(ValidationError) as exc:
        finalize(
            complete(
                borrower={"dateOfBirth": "2999-01-01"},
                income={"startDate": "2999-01-01"},
            )
        )
    assert error_locs(exc) == {("borrower", "dateOfBirth"), ("income", "startDate")}


@pytest.mark.parametrize("field", ["loanAmount", "loanTermMonths"])
def test_loan_amount_and_term_must_be_positive(field):
    with pytest.raises(ValidationError):
        finalize(complete(loan={field: 0}))


def test_partial_subject_address_rejected():
    with pytest.raises(ValidationError) as exc:
        finalize(complete(subjectProperty={"city": "Tucson"}))
    assert error_locs(exc) == {("subjectProperty",)}


def test_complete_subject_address_accepted():
    urla = finalize(complete(subjectProperty=SUBJECT_ADDRESS))
    assert urla.subject_property.has_address is True


def test_refinance_requires_subject_address():
    with pytest.raises(ValidationError, match="refinance"):
        finalize(complete(loan={"loanPurpose": "Refinance"}))


def test_refinance_with_subject_address_finalizes():
    finalize(
        complete(loan={"loanPurpose": "Refinance"}, subjectProperty=SUBJECT_ADDRESS)
    )


def test_installment_requires_months_remaining():
    payload: dict[str, Any] = copy.deepcopy(COMPLETE)
    payload["liabilities"][0]["liabilityType"] = "Installment"
    with pytest.raises(ValidationError) as exc:
        finalize(payload)
    assert error_locs(exc) == {("liabilities", 0)}

    payload["liabilities"][0]["monthsRemaining"] = 36
    finalize(payload)


@pytest.mark.parametrize("liability_type", ["Revolving", "Open30Day", "Lease", "Other"])
def test_other_liabilities_do_not_need_months_remaining(liability_type):
    payload: dict[str, Any] = copy.deepcopy(COMPLETE)
    payload["liabilities"][0]["liabilityType"] = liability_type
    finalize(payload)
