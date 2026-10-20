"""Read a MISMO v3.4 ``MESSAGE`` back into a ``Urla`` (FR-04).

``from_xml`` reads the single-borrower subset that ``to_xml`` emits. It takes
the first ``DEAL``, ``PARTY``, ``ROLE``, ``LOAN``, residence, and employer by
position, and ignores ``RELATIONSHIPS``, because ``to_xml`` writes exactly one
of each and links nothing else. A file from another system (e.g., the DU test
cases) can hold several borrowers, related loans, and prior residences; that
is out of scope (L-03).

Values outside the subset raise ``UnsupportedError`` rather than being mapped
to the nearest URLA value, e.g., a ``GiftOfCash`` asset, a VA loan, or
self-employment income (L-04).
"""

from datetime import date
from decimal import Decimal
from typing import Any, get_args, get_origin

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from ..generated import (
    Address,
    Asset,
    AssetBase,
    AssetDetail,
    Borrower,
    BorrowerResidencyBasisBase,
    ContactPoint,
    CurrentIncomeItem,
    Deal,
    Employer,
    HousingExpense,
    HousingExpenseBase,
    HousingExpenseTimingBase,
    IncomeBase,
    Liability,
    LiabilityBase,
    LiabilityDetail,
    Loan,
    LoanPurposeBase,
    Message,
    MortgageBase,
    Name,
    Party,
    Property,
    PropertyUsageBase,
    Residence,
)
from ..urla import Asset as UrlaAsset
from ..urla import Borrower as UrlaBorrower
from ..urla import (
    CurrentProperty,
    Income,
    LoanInformation,
    SubjectProperty,
    Urla,
)
from ..urla import Liability as UrlaLiability
from .mappings import (
    ASSET_TYPES,
    LIABILITY_TYPES,
    LOAN_PROGRAMS,
    LOAN_PURPOSES,
    OCCUPANCIES,
    OWN_STATUSES,
)


class MissingError(ValueError):
    """A required element is absent."""


class UnsupportedError(ValueError):
    """The XML holds a value the supported URLA subset cannot represent."""


def access[O](value: Any, path: list[str | int], typ: type[O]) -> O:
    tgt: Any = value

    if tgt is None:
        raise TypeError("value is None")

    for p in path:
        if isinstance(p, str):
            tgt = getattr(tgt, p)
        elif isinstance(p, int):
            if not isinstance(tgt, list):
                raise TypeError(
                    f"index {p} needs a list, recv {type(tgt).__name__}, path - {path}"
                )
            tgt = tgt[p] if p < len(tgt) else None
        else:
            raise TypeError(f"path can only be int or str, recv {p}")

        if tgt is None:
            raise MissingError(
                f"missing element: path - {p} in {path}, type - {type(value).__name__}"
            )

    base = get_origin(typ)
    if base is not None:
        if type(tgt) != base:
            raise TypeError(
                f"base type mismatch: req type - {typ}, recv base - {base}, input type - {type(value).__name__}"
            )
        elif base is list and len(tgt):
            args = get_args(typ)

            if args and type(tgt[0]) != args[0]:
                raise TypeError(
                    f"list item type mismatch: req type - {typ}, recv - {tgt[0]}, input type - {type(value).__name__}"
                )

    elif type(tgt) != typ:
        raise TypeError(
            f"type mismatch: req type - {typ}, recv - {type(tgt).__name__}, input type - {type(value).__name__}"
        )

    return tgt


def opt_access[O](value: Any, path: list[str | int], typ: type[O]) -> O | None:
    try:
        return access(value, path, typ)
    except MissingError:
        return None


def convert[M, U](table: dict[U, M], value: M, element: str) -> U:
    """The URLA value for a MISMO enumeration, from a ``mappings`` table."""
    for urla_value, mismo_value in table.items():
        if mismo_value == value:
            return urla_value

    raise UnsupportedError(f"unsupported {element}: {value}")


def format_zip(zip_code: str | None):
    if not zip_code:
        return None
    return zip_code if len(zip_code) <= 5 else f"{zip_code[:5]}-{zip_code[5:]}"


def urla_liabilities(deal: Deal) -> list[UrlaLiability]:
    liabilities = []
    deal_liabilities = opt_access(deal, ["liabilities", "liability"], list[Liability])

    if not deal_liabilities:
        return []

    for liab in deal_liabilities:
        l_detail = access(liab, ["liability_detail"], LiabilityDetail)
        l_type = convert(
            LIABILITY_TYPES,
            access(l_detail, ["liability_type", "value"], LiabilityBase),
            "LiabilityType",
        )
        name = access(liab, ["liability_holder", "name", "full_name", "value"], str)
        months_remain = opt_access(
            l_detail, ["liability_remaining_term_months_count", "value"], int
        )
        balance = access(
            l_detail, ["liability_unpaid_balance_amount", "value"], Decimal
        )
        monthly_amt = access(
            l_detail, ["liability_monthly_payment_amount", "value"], Decimal
        )

        urla_liability = UrlaLiability(
            institution_name=name,
            liability_type=l_type,
            monthly_amount=monthly_amt,
            balance=balance,
            months_remaining=months_remain,
        )

        liabilities.append(urla_liability)

    return liabilities


def urla_assets(deal: Deal) -> list[UrlaAsset]:
    assets = []
    deal_assets = opt_access(deal, ["assets", "asset"], list[Asset])

    if not deal_assets:
        return []

    for asset in deal_assets:
        # Owned real estate (URLA section 3) has no ASSET_DETAIL.
        if asset.owned_property is not None:
            raise UnsupportedError("unsupported asset: owned real estate")

        # The type first: assets outside the subset (e.g., gifts) have no holder.
        asset_detail = access(asset, ["asset_detail"], AssetDetail)
        asset_type = convert(
            ASSET_TYPES,
            access(asset_detail, ["asset_type", "value"], AssetBase),
            "AssetType",
        )
        name = access(asset, ["asset_holder", "name", "full_name", "value"], str)
        amt = access(
            asset_detail, ["asset_cash_or_market_value_amount", "value"], Decimal
        )

        urla_asset = UrlaAsset(
            institution_name=name,
            asset_type=asset_type,
            amount=amt,
        )

        assets.append(urla_asset)

    return assets


def urla_income(borrower: Borrower) -> Income:
    employer = access(borrower, ["employers", "employer", 0], Employer)
    name = access(
        employer, ["legal_entity", "legal_entity_detail", "full_name", "value"], str
    )
    start_date = access(employer, ["employment", "employment_start_date", "value"], str)
    position = opt_access(
        employer, ["employment", "employment_position_description", "value"], str
    )

    current_income_item = opt_access(
        borrower,
        ["current_income", "current_income_items", "current_income_item", 0],
        CurrentIncomeItem,
    )

    if current_income_item is None:
        # A 25%-or-more owner reports one monthly figure on the employer (L-04).
        self_employed = opt_access(
            employer,
            ["employment", "employment_monthly_income_amount", "value"],
            Decimal,
        )

        if self_employed is not None:
            raise UnsupportedError("unsupported income: self-employment")
        raise MissingError("missing element: CURRENT_INCOME_ITEM")

    income_type = access(
        current_income_item,
        ["current_income_item_detail", "income_type", "value"],
        IncomeBase,
    )

    if income_type != IncomeBase.BASE:
        raise UnsupportedError(f"unsupported IncomeType: {income_type}")

    income = access(
        current_income_item,
        ["current_income_item_detail", "current_income_monthly_total_amount", "value"],
        Decimal,
    )

    return Income(
        employer_name=name,
        monthly_income=income,
        start_date=date.fromisoformat(start_date),
        position=position,
    )


def urla_subject_property(deal: Deal, loan: Loan) -> SubjectProperty:
    collateral = access(
        deal, ["collaterals", "collateral", 0, "subject_property"], Property
    )

    address = opt_access(collateral, ["address"], Address)
    street_address = None
    city = None
    state = None
    zip_code = None

    if address:
        street_address = access(address, ["address_line_text", "value"], str)
        city = access(address, ["city_name", "value"], str)
        state = access(address, ["state_code", "value"], str)
        zip_code = access(address, ["postal_code", "value"], str)

    property_usage = access(
        collateral,
        ["property_detail", "property_usage_type", "value"],
        PropertyUsageBase,
    )
    occupancy = convert(OCCUPANCIES, property_usage, "PropertyUsageType")

    property_value = opt_access(
        collateral,
        [
            "property_valuations",
            "property_valuation",
            0,
            "property_valuation_detail",
            "property_valuation_amount",
            "value",
        ],
        Decimal,
    )

    if property_value is None:
        # A purchase without an appraisal yet has only the contract price.
        property_value = access(
            collateral,
            [
                "sales_contracts",
                "sales_contract",
                0,
                "sales_contract_detail",
                "sales_contract_amount",
                "value",
            ],
            Decimal,
        )

    expenses = (
        opt_access(loan, ["housing_expenses", "housing_expense"], list[HousingExpense])
        or []
    )
    monthly_hoi, monthly_taxes = None, None

    for exp in expenses:
        # The borrower's current (Present) housing costs are listed here too.
        timing = opt_access(
            exp, ["housing_expense_timing_type", "value"], HousingExpenseTimingBase
        )

        if timing != HousingExpenseTimingBase.PROPOSED:
            continue

        exp_ty = opt_access(exp, ["housing_expense_type", "value"], HousingExpenseBase)
        amt = opt_access(exp, ["housing_expense_payment_amount", "value"], Decimal)

        match exp_ty:
            case HousingExpenseBase.HOMEOWNERS_INSURANCE:
                monthly_hoi = amt
            case HousingExpenseBase.REAL_ESTATE_TAX:
                monthly_taxes = amt

    return SubjectProperty(
        property_value=property_value,
        occupancy=occupancy,
        street_address=street_address,
        city=city,
        state=state,
        zip_code=format_zip(zip_code),
        monthly_hoi=monthly_hoi,
        monthly_taxes=monthly_taxes,
    )


def urla_borrower(party: Party, borrower: Borrower) -> UrlaBorrower:
    name = access(party, ["individual", "name"], Name)
    first_name = access(name, ["first_name", "value"], str)
    last_name = access(name, ["last_name", "value"], str)

    contact_points = (
        opt_access(
            party, ["individual", "contact_points", "contact_point"], list[ContactPoint]
        )
        or []
    )
    borrower_email, phone_number = None, None

    for cp in contact_points:
        email = opt_access(
            cp, ["contact_point_email", "contact_point_email_value", "value"], str
        )

        if email:
            borrower_email = email

        phone = opt_access(
            cp,
            ["contact_point_telephone", "contact_point_telephone_value", "value"],
            str,
        )

        if phone:
            phone_number = phone

    dob = access(borrower, ["borrower_detail", "borrower_birth_date", "value"], str)

    return UrlaBorrower(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date.fromisoformat(dob),
        email=borrower_email,
        phone_number=phone_number,
    )


def urla_current_property(borrower: Borrower) -> CurrentProperty:
    residence = access(borrower, ["residences", "residence", 0], Residence)
    street_address = access(residence, ["address", "address_line_text", "value"], str)
    city = access(residence, ["address", "city_name", "value"], str)
    state = access(residence, ["address", "state_code", "value"], str)
    zip_code = access(residence, ["address", "postal_code", "value"], str)

    own_basis = access(
        residence,
        ["residence_detail", "borrower_residency_basis_type", "value"],
        BorrowerResidencyBasisBase,
    )

    months_at_address = access(
        residence,
        ["residence_detail", "borrower_residency_duration_months_count", "value"],
        int,
    )

    return CurrentProperty(
        street_address=street_address,
        city=city,
        state=state,
        zip_code=format_zip(zip_code),
        own_status=convert(OWN_STATUSES, own_basis, "BorrowerResidencyBasisType"),
        months_at_address=months_at_address,
    )


def urla_loan_information(loan: Loan) -> LoanInformation:
    loan_term_months = access(
        loan,
        [
            "amortization",
            "amortization_rule",
            "loan_amortization_period_count",
            "value",
        ],
        int,
    )

    mortgage_base = access(
        loan, ["terms_of_loan", "mortgage_type", "value"], MortgageBase
    )
    loan_amount = access(loan, ["terms_of_loan", "base_loan_amount", "value"], Decimal)
    purpose_type = access(
        loan, ["terms_of_loan", "loan_purpose_type", "value"], LoanPurposeBase
    )

    return LoanInformation(
        loan_amount=loan_amount,
        loan_program=convert(LOAN_PROGRAMS, mortgage_base, "MortgageType"),
        loan_purpose=convert(LOAN_PURPOSES, purpose_type, "LoanPurposeType"),
        loan_term_months=loan_term_months,
    )


def from_xml(input: bytes) -> Urla:
    config = ParserConfig()
    context = XmlContext()
    parser = XmlParser(context=context, config=config)

    message = parser.from_bytes(input, Message)

    deal = access(message, ["deal_sets", "deal_set", 0, "deals", "deal", 0], Deal)
    party = access(deal, ["parties", "party", 0], Party)
    borrower = access(party, ["roles", "role", 0, "borrower"], Borrower)
    loan = access(deal, ["loans", "loan", 0], Loan)

    return Urla(
        borrower=urla_borrower(party, borrower),
        address=urla_current_property(borrower),
        subject_property=urla_subject_property(deal, loan),
        income=urla_income(borrower),
        loan=urla_loan_information(loan),
        assets=urla_assets(deal),
        liabilities=urla_liabilities(deal),
    )
