"""URLA enum values and the MISMO enumerations they map to.

One table per enum, read forward by ``to_xml`` and inverted by ``from_xml``,
so the two directions cannot drift apart. Each table must be one-to-one.
"""

from ..generated import (
    AssetBase,
    BorrowerResidencyBasisBase,
    LiabilityBase,
    LoanPurposeBase,
    MortgageBase,
    PropertyUsageBase,
)
from ..urla import (
    AssetType,
    LiabilityType,
    LoanProgram,
    LoanPurpose,
    Occupancy,
    OwnStatus,
)

OWN_STATUSES = {
    OwnStatus.Own: BorrowerResidencyBasisBase.OWN,
    OwnStatus.Rent: BorrowerResidencyBasisBase.RENT,
}

ASSET_TYPES = {
    AssetType.Checking: AssetBase.CHECKING_ACCOUNT,
    AssetType.Savings: AssetBase.SAVINGS_ACCOUNT,
    AssetType.Retirement: AssetBase.RETIREMENT_FUND,
}

LIABILITY_TYPES = {
    LiabilityType.Installment: LiabilityBase.INSTALLMENT,
    LiabilityType.Lease: LiabilityBase.LEASE_PAYMENT,
    LiabilityType.Open30Day: LiabilityBase.OPEN30_DAY_CHARGE_ACCOUNT,
    LiabilityType.Revolving: LiabilityBase.REVOLVING,
    LiabilityType.Other: LiabilityBase.OTHER,
}

OCCUPANCIES = {
    Occupancy.Primary: PropertyUsageBase.PRIMARY_RESIDENCE,
    Occupancy.Second: PropertyUsageBase.SECOND_HOME,
    Occupancy.Investment: PropertyUsageBase.INVESTMENT,
}

LOAN_PROGRAMS = {
    LoanProgram.Conventional: MortgageBase.CONVENTIONAL,
    LoanProgram.Fha: MortgageBase.FHA,
}

LOAN_PURPOSES = {
    LoanPurpose.Purchase: LoanPurposeBase.PURCHASE,
    LoanPurpose.Refinance: LoanPurposeBase.REFINANCE,
}
