from datetime import date
from decimal import Decimal
from typing import Any, get_args, get_origin

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from mismo.generated import HousingExpenseBase, PropertyUsageBase

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
    Residence,
)
from ..urla import Asset as UrlaAsset
from ..urla import (
    AssetType,
    CurrentProperty,
    Income,
    LiabilityType,
    LoanInformation,
    LoanProgram,
    LoanPurpose,
    Occupancy,
    OwnStatus,
    SubjectProperty,
    Urla,
)
from ..urla import Borrower as UrlaBorrower
from ..urla import Liability as UrlaLiability


class MissingError(ValueError):
    pass


def access[O](value: Any, path: list[str | int], typ: type[O]) -> O:
    tgt: Any = value

    if tgt is None:
        raise TypeError("value is None")

    for p in path:
        if isinstance(p, str):
            tgt = getattr(tgt, p)
        elif isinstance(p, int):
            if p < len(tgt):
                tgt = tgt[p]
            else:
                tgt = None
        else:
            raise TypeError(f"path can only be list or str, recv {p}")

        if tgt is None:
            raise MissingError(
                f"missing element: path - {p}, type - {type(value).__name__}"
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
        res = access(value, path, typ)
        return res
    except MissingError:
        return None


def format_zip(zip_code: str | None):
    if not zip_code:
        return None
    return zip_code if len(zip_code) <= 5 else f"{zip_code[:5]}-{zip_code[5:]}"


LIABILITY_TYPES = {
    LiabilityBase.INSTALLMENT: LiabilityType.Installment,
    LiabilityBase.LEASE_PAYMENT: LiabilityType.Lease,
    LiabilityBase.OPEN30_DAY_CHARGE_ACCOUNT: LiabilityType.Open30Day,
    LiabilityBase.REVOLVING: LiabilityType.Revolving,
    LiabilityBase.OTHER: LiabilityType.Other,
}


def liability_type_convert(lb: LiabilityBase) -> LiabilityType:
    try:
        return LIABILITY_TYPES[lb]
    except KeyError:
        return LiabilityType.Other


def urla_liabilities(deal: Deal) -> list[UrlaLiability]:
    liabilities = []
    deal_liabilities = opt_access(deal, ["liabilities", "liability"], list[Liability])

    if not deal_liabilities:
        return []

    for liab in deal_liabilities:
        name = access(liab, ["liability_holder", "name", "full_name", "value"], str)
        l_detail = access(liab, ["liability_detail"], LiabilityDetail)
        months_remain = opt_access(
            l_detail, ["liability_remaining_term_months_count", "value"], int
        )
        l_type = access(l_detail, ["liability_type", "value"], LiabilityBase)
        balance = access(
            l_detail, ["liability_unpaid_balance_amount", "value"], Decimal
        )
        monthly_amt = access(
            l_detail, ["liability_monthly_payment_amount", "value"], Decimal
        )

        urla_liability = UrlaLiability(
            institution_name=name,
            liability_type=liability_type_convert(l_type),
            monthly_amount=monthly_amt,
            balance=balance,
            months_remaining=months_remain,
        )

        liabilities.append(urla_liability)

    return liabilities


ASSET_TYPES = {
    AssetBase.CHECKING_ACCOUNT: AssetType.Checking,
    AssetBase.SAVINGS_ACCOUNT: AssetType.Savings,
    AssetBase.RETIREMENT_FUND: AssetType.Retirement,
}


def asset_type_convert(ab: AssetBase) -> AssetType:
    try:
        return ASSET_TYPES[ab]
    except KeyError:
        raise ValueError(f"unsupported asset type: {ab}")


def urla_assets(deal: Deal) -> list[UrlaAsset]:
    assets = []
    deal_assets = opt_access(deal, ["assets", "asset"], list[Asset])

    if not deal_assets:
        return []

    for asset in deal_assets:
        name = access(asset, ["asset_holder", "name", "full_name", "value"], str)
        asset_detail = access(asset, ["asset_detail"], AssetDetail)
        amt = access(
            asset_detail, ["asset_cash_or_market_value_amount", "value"], Decimal
        )
        asset_type = access(asset_detail, ["asset_type", "value"], AssetBase)

        urla_asset = UrlaAsset(
            institution_name=name,
            asset_type=asset_type_convert(asset_type),
            amount=amt,
        )

        assets.append(urla_asset)

    return assets


def urla_income(deal: Deal) -> Income:
    borrower = access(
        deal, ["parties", "party", 0, "roles", "role", 0, "borrower"], Borrower
    )
    employer = access(borrower, ["employers", "employer", 0], Employer)
    name = access(
        employer, ["legal_entity", "legal_entity_detail", "full_name", "value"], str
    )
    start_date = access(employer, ["employment", "employment_start_date", "value"], str)
    position = opt_access(
        employer, ["employment", "employment_position_description", "value"], str
    )

    current_income_item = access(
        borrower,
        ["current_income", "current_income_items", "current_income_item", 0],
        CurrentIncomeItem,
    )
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


def occupancy_type_convert(ot: PropertyUsageBase) -> Occupancy:
    match ot:
        case PropertyUsageBase.PRIMARY_RESIDENCE:
            return Occupancy.Primary
        case PropertyUsageBase.SECOND_HOME:
            return Occupancy.Second
        case PropertyUsageBase.INVESTMENT:
            return Occupancy.Investment
        case _:
            raise ValueError(f"unsuported occupancy type: {ot}")


def urla_subject_property(deal: Deal) -> SubjectProperty:
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
    occupancy = occupancy_type_convert(property_usage)

    property_value = access(
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

    loan = access(deal, ["loans", "loan", 0], Loan)
    expenses = (
        opt_access(loan, ["housing_expenses", "housing_expense"], list[HousingExpense])
        or []
    )
    monthly_hoi, monthly_taxes = None, None

    for exp in expenses:
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


def urla_borrower(deal: Deal) -> UrlaBorrower:
    party = access(deal, ["parties", "party", 0], Party)

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

    borrower = access(party, ["roles", "role", 0, "borrower"], Borrower)
    dob = access(borrower, ["borrower_detail", "borrower_birth_date", "value"], str)

    return UrlaBorrower(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date.fromisoformat(dob),
        email=borrower_email,
        phone_number=phone_number,
    )


def urla_current_property(deal: Deal):
    residence = access(
        deal,
        [
            "parties",
            "party",
            0,
            "roles",
            "role",
            0,
            "borrower",
            "residences",
            "residence",
            0,
        ],
        Residence,
    )
    street_address = access(residence, ["address", "address_line_text", "value"], str)
    city = access(residence, ["address", "city_name", "value"], str)
    state = access(residence, ["address", "state_code", "value"], str)
    zip_code = access(residence, ["address", "postal_code", "value"], str)

    own_basis = access(
        residence,
        ["residence_detail", "borrower_residency_basis_type", "value"],
        BorrowerResidencyBasisBase,
    )

    match own_basis:
        case BorrowerResidencyBasisBase.OWN:
            own_status = OwnStatus.Own
        case BorrowerResidencyBasisBase.RENT:
            own_status = OwnStatus.Rent
        case _:
            own_status = OwnStatus.Other

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
        own_status=own_status,
        months_at_address=months_at_address,
    )


def urla_loan_information(deal: Deal):
    loan = access(deal, ["loans", "loan", 0], Loan)

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

    match mortgage_base:
        case MortgageBase.FHA:
            loan_program = LoanProgram.Fha
        case MortgageBase.CONVENTIONAL:
            loan_program = LoanProgram.Conventional
        case _:
            raise ValueError(f"unsupported loan program {mortgage_base}")

    loan_amount = access(loan, ["terms_of_loan", "base_loan_amount", "value"], Decimal)

    purpose_type = access(
        loan, ["terms_of_loan", "loan_purpose_type", "value"], LoanPurposeBase
    )

    match purpose_type:
        case LoanPurposeBase.PURCHASE:
            loan_purpose = LoanPurpose.Purchase
        case LoanPurposeBase.REFINANCE:
            loan_purpose = LoanPurpose.Refinance
        case _:
            raise ValueError(f"unsupported loan purpose: {purpose_type}")

    return LoanInformation(
        loan_amount=loan_amount,
        loan_program=loan_program,
        loan_purpose=loan_purpose,
        loan_term_months=loan_term_months,
    )


def from_xml(input: bytes) -> Urla:
    config = ParserConfig()
    context = XmlContext()
    parser = XmlParser(context=context, config=config)

    message = parser.from_bytes(input, Message)

    deal = access(message, ["deal_sets", "deal_set", 0, "deals", "deal", 0], Deal)

    return Urla(
        borrower=urla_borrower(deal),
        address=urla_current_property(deal),
        subject_property=urla_subject_property(deal),
        income=urla_income(deal),
        loan=urla_loan_information(deal),
        assets=urla_assets(deal),
        liabilities=urla_liabilities(deal),
    )
