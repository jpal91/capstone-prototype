from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel
from pydantic_extra_types.phone_numbers import PhoneNumber


class OwnStatus(StrEnum):
    Own = "Own"
    Rent = "Rent"


class AssetType(StrEnum):
    Checking = "Checking"
    Savings = "Savings"
    Retirement = "Retirement"


class LiabilityType(StrEnum):
    Revolving = "Revolving"
    Installment = "Installment"
    Open30Day = "Open30Day"
    Lease = "Lease"
    Other = "Other"


class LoanProgram(StrEnum):
    Conventional = "Conventional"
    Fha = "FHA"


class LoanPurpose(StrEnum):
    Purchase = "Purchase"
    Refinance = "Refinance"


class Occupancy(StrEnum):
    Primary = "PrimaryResidence"
    Second = "SecondHome"
    Investment = "Investment"


class UrlaModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )


class USPhone(PhoneNumber):
    default_region_code = "US"
    phone_format = "E164"


class BorrowerDraft(UrlaModel):
    first_name: str | None = Field(None, min_length=1)
    last_name: str | None = Field(None, min_length=1)
    date_of_birth: date | None = None
    phone_number: USPhone | None = None
    email: EmailStr | None = None


class AddressDraft(UrlaModel):
    street_address: str | None = None
    city: str | None = None
    state: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    zip_code: str | None = Field(None, pattern=r"^\d{5}(-\d{4})?$")


class CurrentPropertyDraft(AddressDraft):
    own_status: OwnStatus | None = None
    months_at_address: int | None = Field(None, ge=0)


class SubjectPropertyDraft(AddressDraft):
    monthly_taxes: Decimal | None = Field(None, ge=0, decimal_places=2)
    monthly_hoi: Decimal | None = Field(None, ge=0, decimal_places=2)
    purchase_price: Decimal | None = Field(None, ge=0, decimal_places=2)
    occupancy: Occupancy | None = None


class IncomeDraft(UrlaModel):
    employer_name: str | None = Field(None, min_length=1)
    monthly_income: Decimal | None = Field(None, ge=0, decimal_places=2)
    start_date: date | None = None
    position: str | None = Field(None, min_length=1)


class AssetDraft(UrlaModel):
    institution_name: str | None = Field(None, min_length=1)
    asset_type: AssetType | None = None
    amount: Decimal | None = Field(None, ge=0, decimal_places=2)


class LiabilityDraft(UrlaModel):
    institution_name: str | None = Field(None, min_length=1)
    liability_type: LiabilityType | None = None
    months_remaining: int | None = Field(None, ge=0)
    monthly_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    balance: Decimal | None = Field(None, ge=0, decimal_places=2)


class LoanInformationDraft(UrlaModel):
    loan_term_months: int | None = Field(None, ge=0)
    loan_program: LoanProgram | None = None
    loan_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    loan_purpose: LoanPurpose | None = None


class UrlaDraft(UrlaModel):
    borrower: BorrowerDraft = Field(default_factory=BorrowerDraft)
    address: CurrentPropertyDraft = Field(default_factory=CurrentPropertyDraft)
    subject_property: SubjectPropertyDraft = Field(default_factory=SubjectPropertyDraft)
    income: IncomeDraft = Field(default_factory=IncomeDraft)
    assets: list[AssetDraft] = Field(default_factory=list)
    liabilities: list[LiabilityDraft] = Field(default_factory=list)
    loan: LoanInformationDraft = Field(default_factory=LoanInformationDraft)
