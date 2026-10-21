"""Data and steps shared by more than one test module."""

from typing import Any

from fastapi.testclient import TestClient

# A draft that passes the strict model. Synthetic (NFR-06).
COMPLETE: dict[str, Any] = {
    "borrower": {
        "firstName": "Alex",
        "lastName": "Example",
        "dateOfBirth": "1990-01-01",
    },
    "address": {
        "streetAddress": "100 Example Ave",
        "city": "Tucson",
        "state": "AZ",
        "zipCode": "85701",
        "ownStatus": "Rent",
        "monthsAtAddress": 24,
    },
    "subjectProperty": {"propertyValue": "350000.00", "occupancy": "PrimaryResidence"},
    "income": {
        "employerName": "Example Corp",
        "monthlyIncome": "6000.00",
        "startDate": "2020-05-01",
    },
    "assets": [
        {
            "institutionName": "Example Bank",
            "assetType": "Checking",
            "amount": "1000.00",
        }
    ],
    "liabilities": [
        {
            "institutionName": "Example Card",
            "liabilityType": "Revolving",
            "monthlyAmount": "50.00",
            "balance": "900.00",
        }
    ],
    "loan": {
        "loanTermMonths": 360,
        "loanProgram": "Conventional",
        "loanAmount": "280000.00",
        "loanPurpose": "Purchase",
    },
}


def finalize(
    client: TestClient, headers: dict[str, str], draft: dict[str, Any] = COMPLETE
) -> dict[str, Any]:
    assert client.put("/draft", headers=headers, json=draft).status_code == 204
    response = client.post("/draft/finalize", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
