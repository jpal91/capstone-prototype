"""Data model for the supported subset of the URLA (Form 1003).

There are two versions of each model:

- ``*Draft`` models are what the borrower edits and saves. Every field is
  optional, so a half-finished application can be saved at any point (FR-01).
- The strict models (``Urla`` and the models it contains) describe a complete
  pre-application. Finalizing validates a draft against them before the MISMO
  mapper runs::

      Urla.model_validate(draft.model_dump(by_alias=True, exclude_none=True))

  Field names are the same in both, so a failed validation lists exactly
  what is still missing. Dumping by alias keeps every error location in the
  camelCase the portal sent; dropping ``None`` reports empty fields as
  missing rather than as the wrong type.

All models share ``UrlaModel``'s configuration:

- ``extra="forbid"`` rejects any key that isn't modelled. Nothing outside the
  supported subset is ever stored; in particular, an SSN or HMDA field is
  refused rather than silently dropped (NFR-01, NFR-02).
- JSON keys are camelCase (``firstName``) for the portal; snake_case names
  are also accepted.

Enum values use MISMO v3.4 spellings so the mapper can copy them through
unchanged, which keeps the round trip lossless (FR-04).
TODO: verify every enum value against the XSD once it is available.

Docstrings cite the URLA section each model covers. Sections starting with
"L" are the lender's part of the form; the borrower supplies these as stated
preferences.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PastDate, model_validator
from pydantic.alias_generators import to_camel
from pydantic_extra_types.phone_numbers import PhoneNumber


class OwnStatus(StrEnum):
    Own = "Own"
    Rent = "Rent"
    Other = "Other"


class AssetType(StrEnum):
    Checking = "Checking"
    Savings = "Savings"
    Retirement = "Retirement"
    Other = "Other"


class LiabilityType(StrEnum):
    Revolving = "Revolving"
    Installment = "Installment"
    Open30Day = "Open30Day"
    Lease = "Lease"
    Other = "Other"


class LoanProgram(StrEnum):
    Conventional = "Conventional"
    Fha = "FHA"
    Other = "Other"


class LoanPurpose(StrEnum):
    Purchase = "Purchase"
    Refinance = "Refinance"
    Other = "Other"


class Occupancy(StrEnum):
    Primary = "PrimaryResidence"
    Second = "SecondHome"
    Investment = "Investment"
    Other = "Other"


class UrlaModel(BaseModel):
    """Base for every URLA model: camelCase JSON, unknown keys rejected."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )


class USPhone(PhoneNumber):
    """Phone number; US is assumed when no country code is given. Stored as E.164."""

    default_region_code = "US"
    supported_regions = ["US"]  # noqa RUF012
    phone_format = "E164"


# --- Drafts: everything optional ---------------------------------------------


class BorrowerDraft(UrlaModel):
    """1a. Personal Information."""

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
    """1a. Current address, housing (own/rent), and time at the address."""

    own_status: OwnStatus | None = None
    months_at_address: int | None = Field(None, ge=0)


class SubjectPropertyDraft(AddressDraft):
    """4a. The property being purchased or refinanced."""

    monthly_taxes: Decimal | None = Field(None, ge=0, decimal_places=2)
    monthly_hoi: Decimal | None = Field(None, ge=0, decimal_places=2)
    property_value: Decimal | None = Field(None, ge=0, decimal_places=2)
    occupancy: Occupancy | None = None


class IncomeDraft(UrlaModel):
    """1b. Current employment and income (one employer)."""

    employer_name: str | None = Field(None, min_length=1)
    monthly_income: Decimal | None = Field(None, ge=0, decimal_places=2)
    start_date: date | None = None
    position: str | None = Field(None, min_length=1)


class AssetDraft(UrlaModel):
    """2a. One bank, retirement, or other account."""

    institution_name: str | None = Field(None, min_length=1)
    asset_type: AssetType | None = None
    amount: Decimal | None = Field(None, ge=0, decimal_places=2)


class LiabilityDraft(UrlaModel):
    """2c. One credit card, other debt, or lease."""

    institution_name: str | None = Field(None, min_length=1)
    liability_type: LiabilityType | None = None
    months_remaining: int | None = Field(None, ge=0)
    monthly_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    balance: Decimal | None = Field(None, ge=0, decimal_places=2)


class LoanInformationDraft(UrlaModel):
    """4a. Loan amount and purpose; L3. Mortgage type and term (borrower's preference)."""

    loan_term_months: int | None = Field(None, ge=0)
    loan_program: LoanProgram | None = None
    loan_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    loan_purpose: LoanPurpose | None = None


class UrlaDraft(UrlaModel):
    """The borrower's editable application. Any subset of fields may be filled in."""

    borrower: BorrowerDraft = Field(default_factory=BorrowerDraft)
    address: CurrentPropertyDraft = Field(default_factory=CurrentPropertyDraft)
    subject_property: SubjectPropertyDraft = Field(default_factory=SubjectPropertyDraft)
    income: IncomeDraft = Field(default_factory=IncomeDraft)
    assets: list[AssetDraft] = Field(default_factory=list)
    liabilities: list[LiabilityDraft] = Field(default_factory=list)
    loan: LoanInformationDraft = Field(default_factory=LoanInformationDraft)


# --- Finalized: a complete pre-application -----------------------------------


class Borrower(UrlaModel):
    """1a. Personal Information."""

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    date_of_birth: PastDate
    phone_number: USPhone | None = None
    email: EmailStr | None = None


class Address(UrlaModel):
    street_address: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(pattern=r"^[A-Z]{2}$")
    zip_code: str = Field(pattern=r"^\d{5}(-\d{4})?$")


class CurrentProperty(Address):
    """1a. Current address, housing (own/rent), and time at the address."""

    own_status: OwnStatus
    months_at_address: int = Field(ge=0)


class SubjectProperty(UrlaModel):
    """4a. The property being purchased or refinanced.

    The address is optional because a purchase may not have a property yet
    (the URLA allows "TBD"). If given, it must be complete. ``Urla`` requires
    it for a refinance.
    """

    street_address: str | None = Field(None, min_length=1)
    city: str | None = Field(None, min_length=1)
    state: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    zip_code: str | None = Field(None, pattern=r"^\d{5}(-\d{4})?$")
    monthly_taxes: Decimal | None = Field(None, ge=0, decimal_places=2)
    monthly_hoi: Decimal | None = Field(None, ge=0, decimal_places=2)
    property_value: Decimal = Field(gt=0, decimal_places=2)
    occupancy: Occupancy

    @property
    def has_address(self) -> bool:
        return self.street_address is not None

    @property
    def address(self) -> Address | None:
        """The address as an ``Address``, or None if it was left empty ("TBD")."""
        if (
            self.street_address is None
            or self.city is None
            or self.state is None
            or self.zip_code is None
        ):
            return None
        return Address(
            street_address=self.street_address,
            city=self.city,
            state=self.state,
            zip_code=self.zip_code,
        )

    @model_validator(mode="after")
    def address_all_or_nothing(self) -> Self:
        parts = (self.street_address, self.city, self.state, self.zip_code)
        if any(p is not None for p in parts) and any(p is None for p in parts):
            raise ValueError("subject property address must be complete or left empty")
        return self


class Income(UrlaModel):
    """1b. Current employment and income (one employer)."""

    employer_name: str = Field(min_length=1)
    monthly_income: Decimal = Field(ge=0, decimal_places=2)
    start_date: PastDate
    position: str | None = Field(None, min_length=1)


class Asset(UrlaModel):
    """2a. One bank, retirement, or other account."""

    institution_name: str = Field(min_length=1)
    asset_type: AssetType
    amount: Decimal = Field(ge=0, decimal_places=2)


class Liability(UrlaModel):
    """2c. One credit card, other debt, or lease.

    ``months_remaining`` is required only for installment debts; a revolving
    account has no fixed number of months left.
    """

    institution_name: str = Field(min_length=1)
    liability_type: LiabilityType
    months_remaining: int | None = Field(None, ge=0)
    monthly_amount: Decimal = Field(ge=0, decimal_places=2)
    balance: Decimal = Field(ge=0, decimal_places=2)

    @model_validator(mode="after")
    def installment_needs_months(self) -> Self:
        if (
            self.liability_type == LiabilityType.Installment
            and self.months_remaining is None
        ):
            raise ValueError(
                "months_remaining is required for an installment liability"
            )
        return self


class LoanInformation(UrlaModel):
    """4a. Loan amount and purpose; L3. Mortgage type and term (borrower's preference)."""

    loan_term_months: int = Field(gt=0)
    loan_program: LoanProgram
    loan_amount: Decimal = Field(gt=0, decimal_places=2)
    loan_purpose: LoanPurpose


class Urla(UrlaModel):
    """A complete pre-application: the input to the MISMO mapper.

    Not collected, by design: SSN (NFR-01), HMDA demographics (NFR-02), a
    co-borrower (L-03), and account numbers.
    """

    borrower: Borrower
    address: CurrentProperty
    subject_property: SubjectProperty
    income: Income
    assets: list[Asset] = Field(default_factory=list)
    liabilities: list[Liability] = Field(default_factory=list)
    loan: LoanInformation

    @model_validator(mode="after")
    def refinance_needs_address(self) -> Self:
        if (
            self.loan.loan_purpose == LoanPurpose.Refinance
            and not self.subject_property.has_address
        ):
            raise ValueError("a refinance requires the subject property address")
        return self
