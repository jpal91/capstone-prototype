"""Map a finalized ``Urla`` onto a MISMO v3.4 ``MESSAGE`` (FR-02, FR-03).

Each builder fills one MISMO container from one part of the URLA; ``to_xml``
assembles them into a single ``DEAL`` and serializes it. Placement follows
Fannie Mae's DU Specification test cases.

Only what the borrower entered is emitted, plus the structural values MISMO
needs to place it (party role, loan role, residency type, income type). No
SSN or HMDA data exists to emit (NFR-01, NFR-02), so the output validates
against the DU wrapper schema but is not DU-submittable (L-02).

The XML is linked with xlink labels: the builders label each asset,
liability, income item, employer, and the borrower role, and
``relationships`` connects them. The XSD does not check that the labels
match, so the tests do.
"""

from lxml import etree  # ty: ignore
from xsdata.formats.dataclass.serializers.tree import TreeSerializer

from ..generated import (
    Address,
    Amortization,
    AmortizationRule,
    Asset,
    AssetBase,
    AssetDetail,
    AssetEnum,
    AssetHolder,
    Assets,
    Borrower,
    BorrowerDetail,
    BorrowerResidencyBase,
    BorrowerResidencyBasisBase,
    BorrowerResidencyBasisEnum,
    BorrowerResidencyEnum,
    Collateral,
    Collaterals,
    ContactPoint,
    ContactPointEmail,
    ContactPoints,
    ContactPointTelephone,
    CurrentIncome,
    CurrentIncomeItem,
    CurrentIncomeItemDetail,
    CurrentIncomeItems,
    Deal,
    Deals,
    DealSet,
    DealSets,
    Employer,
    Employers,
    Employment,
    EmploymentClassificationBase,
    EmploymentClassificationEnum,
    EmploymentStatusBase,
    EmploymentStatusEnum,
    HousingExpense,
    HousingExpenseBase,
    HousingExpenseEnum,
    HousingExpenses,
    HousingExpenseTimingBase,
    HousingExpenseTimingEnum,
    IncomeBase,
    IncomeEnum,
    Individual,
    LegalEntity,
    LegalEntityDetail,
    Liabilities,
    Liability,
    LiabilityBase,
    LiabilityDetail,
    LiabilityEnum,
    LiabilityHolder,
    Loan,
    LoanAmortizationPeriodBase,
    LoanAmortizationPeriodEnum,
    LoanDetail,
    LoanPurposeBase,
    LoanPurposeEnum,
    LoanRoleBase,
    Loans,
    Message,
    Mismoamount,
    Mismocode,
    Mismocount,
    Mismodate,
    Mismoindicator,
    MismonumericString,
    Mismostring,
    Mismovalue,
    MortgageBase,
    MortgageEnum,
    Name,
    Parties,
    Party,
    PartyRoleBase,
    PartyRoleEnum,
    Property,
    PropertyDetail,
    PropertyUsageBase,
    PropertyUsageEnum,
    PropertyValuation,
    PropertyValuationDetail,
    PropertyValuations,
    Relationship,
    Relationships,
    Residence,
    ResidenceDetail,
    Residences,
    Role,
    RoleDetail,
    Roles,
    SalesContract,
    SalesContractDetail,
    SalesContracts,
    TermsOfLoan,
)
from ..urla import Address as UrlaAddress
from ..urla import (
    AssetType,
    LiabilityType,
    LoanProgram,
    LoanPurpose,
    Occupancy,
    OwnStatus,
    Urla,
)


def mismo_address(a: UrlaAddress) -> Address:
    """An ``ADDRESS``. ZIP+4 loses its hyphen, as in the DU test cases."""
    return Address(
        address_line_text=Mismostring(value=a.street_address),
        city_name=Mismostring(value=a.city),
        postal_code=Mismocode(value=a.zip_code.replace("-", "")),
        state_code=Mismocode(value=a.state),
    )


def borrower_residence(urla: Urla) -> Residences:
    """1a. Current address, housing, and time there: the borrower's ``RESIDENCES``."""
    address = urla.address
    residence = Residence(
        address=mismo_address(address),
        residence_detail=ResidenceDetail(
            borrower_residency_basis_type=BorrowerResidencyBasisEnum(
                value=BorrowerResidencyBasisBase.RENT
                if address.own_status == OwnStatus.Rent
                else BorrowerResidencyBasisBase.OWN
            ),
            borrower_residency_duration_months_count=Mismocount(
                value=address.months_at_address
            ),
            borrower_residency_type=BorrowerResidencyEnum(
                value=BorrowerResidencyBase.CURRENT
            ),
        ),
    )

    residences = Residences(residence=[residence])
    return residences


def borrower_employer(urla: Urla) -> Employers:
    """1b. Current employer: the borrower's ``EMPLOYERS``, labelled ``EMPLOYER_1``."""
    urla_inc = urla.income
    employer = Employer(
        sequence_number=1,
        label="EMPLOYER_1",
        legal_entity=LegalEntity(
            legal_entity_detail=LegalEntityDetail(
                full_name=Mismostring(value=urla_inc.employer_name)
            )
        ),
        employment=Employment(
            employment_start_date=Mismodate(value=urla_inc.start_date.isoformat()),
            employment_status_type=EmploymentStatusEnum(
                value=EmploymentStatusBase.CURRENT
            ),
            employment_classification_type=EmploymentClassificationEnum(
                value=EmploymentClassificationBase.PRIMARY
            ),
            employment_position_description=Mismostring(value=urla_inc.position)
            if urla_inc.position
            else None,
        ),
    )
    employers = Employers(employer=[employer])

    return employers


def borrower_income(urla: Urla) -> CurrentIncome:
    """1b. Monthly base income from that employer: ``CURRENT_INCOME``."""
    urla_inc = urla.income
    current_income = CurrentIncomeItem(
        sequence_number=1,
        label="CURRENT_INCOME_ITEM_1",
        current_income_item_detail=CurrentIncomeItemDetail(
            current_income_monthly_total_amount=Mismoamount(
                value=urla_inc.monthly_income
            ),
            employment_income_indicator=Mismoindicator(value=True),
            income_type=IncomeEnum(value=IncomeBase.BASE),
        ),
    )

    current_income_items = CurrentIncomeItems(current_income_item=[current_income])
    current_income = CurrentIncome(current_income_items=current_income_items)
    return current_income


def borrower_role(urla: Urla) -> Role:
    """The borrower ``ROLE`` (``BORROWER_1``), which holds the 1a and 1b data."""
    urla_bwr = urla.borrower

    borrower = Borrower(
        borrower_detail=BorrowerDetail(
            borrower_birth_date=Mismodate(value=urla_bwr.date_of_birth.isoformat())
        ),
        employers=borrower_employer(urla),
        residences=borrower_residence(urla),
        current_income=borrower_income(urla),
    )

    role = Role(
        sequence_number=1,
        label="BORROWER_1",
        borrower=borrower,
        role_detail=RoleDetail(
            party_role_type=PartyRoleEnum(value=PartyRoleBase.BORROWER)
        ),
    )

    return role


def borrower_parties(urla: Urla) -> Parties:
    """1a. Name and contact details: the borrower's ``PARTY``.

    MISMO allows only digits in a phone number, so the ``+1`` is dropped.
    ``USPhone`` accepts only US numbers, so it can be restored on parsing.
    """
    borrower = urla.borrower

    cp_email = (
        ContactPoint(
            contact_point_email=ContactPointEmail(
                contact_point_email_value=Mismovalue(value=borrower.email)
            )
        )
        if borrower.email
        else None
    )

    cp_phone = (
        ContactPoint(
            contact_point_telephone=ContactPointTelephone(
                contact_point_telephone_value=MismonumericString(
                    value=borrower.phone_number.removeprefix("+1")
                )
            )
        )
        if borrower.phone_number
        else None
    )

    party = Party(
        individual=Individual(
            name=Name(
                first_name=Mismostring(value=borrower.first_name),
                last_name=Mismostring(value=borrower.last_name),
            ),
            contact_points=ContactPoints(
                contact_point=[c for c in [cp_email, cp_phone] if c is not None]
            )
            if cp_phone or cp_email
            else None,
        ),
        roles=Roles(role=[borrower_role(urla)]),
    )

    return Parties(party=[party])


ASSET_TYPES = {
    AssetType.Checking: AssetBase.CHECKING_ACCOUNT,
    AssetType.Savings: AssetBase.SAVINGS_ACCOUNT,
    AssetType.Retirement: AssetBase.RETIREMENT_FUND,
}


def asset_type(at: AssetType) -> AssetEnum:
    """The MISMO ``AssetType`` for a URLA asset type."""
    return AssetEnum(value=ASSET_TYPES[at])


def borrower_assets(urla: Urla) -> Assets | None:
    """2a. Accounts: ``ASSETS``, labelled ``ASSET_1`` onward. None if there are none."""
    if not urla.assets:
        return None

    asset_list = [
        Asset(
            sequence_number=i + 1,
            label=f"ASSET_{i + 1}",
            asset_detail=AssetDetail(
                asset_cash_or_market_value_amount=Mismoamount(value=a.amount),
                asset_type=asset_type(a.asset_type),
            ),
            asset_holder=AssetHolder(
                name=Name(full_name=Mismostring(value=a.institution_name))
            ),
        )
        for i, a in enumerate(urla.assets)
    ]

    return Assets(asset=asset_list)


def property_usage(occ: Occupancy) -> PropertyUsageEnum:
    """The MISMO ``PropertyUsageType`` for an occupancy."""
    value = None

    match occ:
        case Occupancy.Primary:
            value = PropertyUsageBase.PRIMARY_RESIDENCE
        case Occupancy.Second:
            value = PropertyUsageBase.SECOND_HOME
        case Occupancy.Investment:
            value = PropertyUsageBase.INVESTMENT

    return PropertyUsageEnum(value=value)


def borrower_collateral(urla: Urla) -> Collaterals:
    """4a. The subject property: ``COLLATERALS``.

    The URLA subset has one property value, so a purchase also reports it as
    the sales contract amount. A refinance has no sales contract.
    """
    sp = urla.subject_property
    address = sp.address

    collateral = Collateral(
        subject_property=Property(
            address=mismo_address(address) if address else None,
            property_detail=PropertyDetail(
                property_usage_type=property_usage(sp.occupancy)
            ),
            property_valuations=PropertyValuations(
                property_valuation=[
                    PropertyValuation(
                        property_valuation_detail=PropertyValuationDetail(
                            property_valuation_amount=Mismoamount(
                                value=sp.property_value
                            )
                        )
                    )
                ]
            ),
            sales_contracts=SalesContracts(
                sales_contract=[
                    SalesContract(
                        sales_contract_detail=SalesContractDetail(
                            sales_contract_amount=Mismoamount(value=sp.property_value)
                        )
                    )
                ]
            )
            if urla.loan.loan_purpose == LoanPurpose.Purchase
            else None,
        )
    )

    return Collaterals(collateral=[collateral])


def liability_type(lt: LiabilityType) -> LiabilityEnum:
    """The MISMO ``LiabilityType`` for a URLA liability type."""
    value = None

    match lt:
        case LiabilityType.Installment:
            value = LiabilityBase.INSTALLMENT
        case LiabilityType.Lease:
            value = LiabilityBase.LEASE_PAYMENT
        case LiabilityType.Open30Day:
            value = LiabilityBase.OPEN30_DAY_CHARGE_ACCOUNT
        case LiabilityType.Revolving:
            value = LiabilityBase.REVOLVING
        case _:
            value = LiabilityBase.OTHER

    return LiabilityEnum(value=value)


def borrower_liabilities(urla: Urla) -> Liabilities | None:
    """2c. Debts: ``LIABILITIES``, labelled ``LIABILITY_1`` onward. None if none."""
    if not urla.liabilities:
        return None

    liability_list = [
        Liability(
            sequence_number=i + 1,
            label=f"LIABILITY_{i + 1}",
            liability_detail=LiabilityDetail(
                liability_monthly_payment_amount=Mismoamount(value=l.monthly_amount),
                liability_remaining_term_months_count=Mismocount(
                    value=l.months_remaining
                )
                if l.months_remaining is not None
                else None,
                liability_type=liability_type(l.liability_type),
                liability_unpaid_balance_amount=Mismoamount(value=l.balance),
            ),
            liability_holder=LiabilityHolder(
                name=Name(full_name=Mismostring(value=l.institution_name))
            ),
        )
        for i, l in enumerate(urla.liabilities)
    ]

    return Liabilities(liability=liability_list)


def mortgage_type(lp: LoanProgram) -> MortgageEnum:
    """The MISMO ``MortgageType`` for a loan program."""
    value = None

    match lp:
        case LoanProgram.Fha:
            value = MortgageBase.FHA
        case _:
            value = MortgageBase.CONVENTIONAL

    return MortgageEnum(value=value)


def borrower_loans(urla: Urla) -> Loans:
    """4a and L3. The subject ``LOAN``: amount, purpose, mortgage type, term.

    Proposed taxes and insurance from 4a become ``HOUSING_EXPENSES``.
    """
    l_info = urla.loan
    subject = urla.subject_property
    housing_expense = []

    if subject.monthly_hoi is not None:
        housing_expense.append(
            HousingExpense(
                housing_expense_payment_amount=Mismoamount(value=subject.monthly_hoi),
                housing_expense_timing_type=HousingExpenseTimingEnum(
                    value=HousingExpenseTimingBase.PROPOSED
                ),
                housing_expense_type=HousingExpenseEnum(
                    value=HousingExpenseBase.HOMEOWNERS_INSURANCE
                ),
            )
        )

    if subject.monthly_taxes is not None:
        housing_expense.append(
            HousingExpense(
                housing_expense_payment_amount=Mismoamount(value=subject.monthly_taxes),
                housing_expense_timing_type=HousingExpenseTimingEnum(
                    value=HousingExpenseTimingBase.PROPOSED
                ),
                housing_expense_type=HousingExpenseEnum(
                    value=HousingExpenseBase.REAL_ESTATE_TAX
                ),
            )
        )

    loan = Loan(
        loan_role_type=LoanRoleBase.SUBJECT_LOAN,
        label="LOAN_1",
        amortization=Amortization(
            amortization_rule=AmortizationRule(
                loan_amortization_period_count=Mismocount(
                    value=l_info.loan_term_months
                ),
                loan_amortization_period_type=LoanAmortizationPeriodEnum(
                    value=LoanAmortizationPeriodBase.MONTH
                ),
            )
        ),
        housing_expenses=HousingExpenses(housing_expense=housing_expense)
        if housing_expense
        else None,
        loan_detail=LoanDetail(
            borrower_count=Mismocount(value=1),
            total_mortgaged_properties_count=Mismocount(value=1),
        ),
        terms_of_loan=TermsOfLoan(
            base_loan_amount=Mismoamount(value=l_info.loan_amount),
            loan_purpose_type=LoanPurposeEnum(
                value=LoanPurposeBase.PURCHASE
                if l_info.loan_purpose == LoanPurpose.Purchase
                else LoanPurposeBase.REFINANCE,
            ),
            mortgage_type=mortgage_type(l_info.loan_program),
        ),
    )

    return Loans(loan=[loan])


ARCROLE = "urn:fdc:mismo.org:2009:residential/{}"


def relationships(urla: Urla) -> Relationships:
    """``RELATIONSHIPS`` linking each asset and liability to the borrower role,
    and the income item to its employer, using the builders' labels.
    """
    links = [
        (f"ASSET_{i}", "BORROWER_1", "ASSET_IsAssociatedWith_ROLE")
        for i in range(1, len(urla.assets) + 1)
    ]
    links += [
        (f"LIABILITY_{i}", "BORROWER_1", "LIABILITY_IsAssociatedWith_ROLE")
        for i in range(1, len(urla.liabilities) + 1)
    ]
    links.append((
        "CURRENT_INCOME_ITEM_1",
        "EMPLOYER_1",
        "CURRENT_INCOME_ITEM_IsAssociatedWith_EMPLOYER",
    ))
    return Relationships(
        relationship=[
            Relationship(
                sequence_number=n, from_value=src, to=dst, arcrole=ARCROLE.format(role)
            )
            for n, (src, dst, role) in enumerate(links, start=1)
        ]
    )


MISMO_NS = "http://www.mismo.org/residential/2009/schemas"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def to_xml(urla: Urla) -> bytes:
    """Serialize a finalized application as UTF-8 MISMO XML.

    xsdata writes every unset nillable element as ``xsi:nil``. Those are
    removed: they would claim a value is deliberately empty, and in a
    choice (such as fax or telephone) they make the document invalid.
    """
    deal = Deal(
        assets=borrower_assets(urla),
        collaterals=borrower_collateral(urla),
        liabilities=borrower_liabilities(urla),
        loans=borrower_loans(urla),
        parties=borrower_parties(urla),
        relationships=relationships(urla),
    )

    root = Message(deal_sets=DealSets(deal_set=[DealSet(deals=Deals(deal=[deal]))]))

    tree = TreeSerializer().render(
        root, ns_map={None: MISMO_NS, "xlink": "http://www.w3.org/1999/xlink"}
    )

    for el in [e for e in tree.iter() if e.get(XSI_NIL) == "true"]:
        el.getparent().remove(el)

    etree.cleanup_namespaces(tree)
    out = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")

    return out
