"""Draft data for the scenarios. Synthetic (NFR-06)."""

import copy
from datetime import UTC, datetime, timedelta
from typing import Any

ABSENT_ID = 2**31 - 1  # the largest ID core's database can hold, so unused

# A draft that passes core's finalize checks. The name marks data eval/ made.
COMPLETE: dict[str, Any] = {
    "borrower": {
        "firstName": "Evan",
        "lastName": "Eval",
        "dateOfBirth": "1988-03-14",
    },
    "address": {
        "streetAddress": "200 Sample St",
        "city": "Tucson",
        "state": "AZ",
        "zipCode": "85701",
        "ownStatus": "Rent",
        "monthsAtAddress": 36,
    },
    "subjectProperty": {"propertyValue": "410000.00", "occupancy": "PrimaryResidence"},
    "income": {
        "employerName": "Sample Works",
        "monthlyIncome": "7250.00",
        "startDate": "2019-08-01",
    },
    "assets": [
        {
            "institutionName": "Sample Bank",
            "assetType": "Checking",
            "amount": "15000.00",
        }
    ],
    "liabilities": [
        {
            "institutionName": "Sample Card",
            "liabilityType": "Revolving",
            "monthlyAmount": "75.00",
            "balance": "1200.00",
        }
    ],
    "loan": {
        "loanTermMonths": 360,
        "loanProgram": "Conventional",
        "loanAmount": "328000.00",
        "loanPurpose": "Purchase",
    },
}


def complete(**changes: dict[str, Any]) -> dict[str, Any]:
    """A copy of COMPLETE with the given sections updated."""
    draft = copy.deepcopy(COMPLETE)
    for section, values in changes.items():
        draft[section].update(values)
    return draft


def every_field() -> dict[str, Any]:
    """COMPLETE with every optional field filled in, so more XML is emitted.

    Values differ between fields, so a mapper that swaps two of them is caught.
    """
    draft = complete(
        borrower={"phoneNumber": "+15205550123", "email": "evan@example.com"},
        subjectProperty={
            "streetAddress": "300 Sample Rd",
            "city": "Santa Fe",
            "state": "NM",
            "zipCode": "87501",
            "monthlyTaxes": "310.00",
            "monthlyHoi": "95.00",
            "occupancy": "SecondHome",
        },
        income={"position": "Analyst"},
        loan={"loanProgram": "FHA", "loanPurpose": "Refinance"},
    )
    draft["assets"].append(
        {
            "institutionName": "Sample Credit Union",
            "assetType": "Savings",
            "amount": "4000.00",
        }
    )
    draft["liabilities"].append(
        {
            "institutionName": "Sample Auto",
            "liabilityType": "Installment",
            "monthsRemaining": 24,
            "monthlyAmount": "310.00",
            "balance": "7440.00",
        }
    )
    return draft


def expires_in(**delta: float) -> str:
    """An `expiresAt` value, relative to now: expires_in(days=1)."""
    return (datetime.now(UTC) + timedelta(**delta)).isoformat()


def drop_nulls(value: Any) -> Any:
    """`value` without null dict entries: core fills in unset optional fields.

    A null inside a list stays, so a broken row still fails a comparison.
    """
    if isinstance(value, dict):
        return {k: drop_nulls(v) for k, v in value.items() if v is not None}
    elif isinstance(value, list):
        return [drop_nulls(item) for item in value]
    else:
        return value
