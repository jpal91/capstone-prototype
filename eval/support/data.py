"""Draft data for the scenarios. Synthetic (NFR-06)."""

import copy
from typing import Any

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
