"""Synthetic applications shared by the tests (NFR-06: no real data)."""

from mismo.urla import Urla

BASE = {
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
    "subjectProperty": {
        "propertyValue": "350000.00",
        "occupancy": "PrimaryResidence",
    },
    "income": {
        "employerName": "Example Corp",
        "monthlyIncome": "6000.00",
        "startDate": "2020-05-01",
    },
    "loan": {
        "loanTermMonths": 360,
        "loanProgram": "Conventional",
        "loanAmount": "280000.00",
        "loanPurpose": "Purchase",
    },
}

ASSET = {
    "institutionName": "Example Bank",
    "assetType": "Checking",
    "amount": "1000.00",
}
LIABILITY = {
    "institutionName": "Example Card",
    "liabilityType": "Revolving",
    "monthlyAmount": "50.00",
    "balance": "900.00",
}


def application(assets: int, liabilities: int) -> Urla:
    return Urla.model_validate(
        {**BASE, "assets": [ASSET] * assets, "liabilities": [LIABILITY] * liabilities}
    )


# Every optional field filled, every asset and liability type, FHA refinance.
FULL = Urla.model_validate(
    {
        **BASE,
        "borrower": {
            **BASE["borrower"],
            "email": "alex@example.com",
            "phoneNumber": "+1 520 555 0100",
        },
        "address": {**BASE["address"], "zipCode": "85701-1234"},
        "subjectProperty": {
            **BASE["subjectProperty"],
            "streetAddress": "1 Test Ln",
            "city": "Tucson",
            "state": "AZ",
            "zipCode": "85702",
            "monthlyHoi": "100.00",
            "monthlyTaxes": "250.00",
        },
        "income": {**BASE["income"], "position": "Engineer"},
        "loan": {**BASE["loan"], "loanPurpose": "Refinance", "loanProgram": "FHA"},
        "assets": [
            ASSET,
            {**ASSET, "assetType": "Savings"},
            {**ASSET, "assetType": "Retirement"},
        ],
        "liabilities": [
            {**LIABILITY, "liabilityType": liability_type, "monthsRemaining": 12}
            for liability_type in (
                "Revolving",
                "Installment",
                "Open30Day",
                "Lease",
                "Other",
            )
        ],
    }
)
