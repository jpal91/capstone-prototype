from decimal import Decimal

from ..generated import (
    Address,
    Amortization,
    AmortizationBase,
    AmortizationEnum,
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
    LienPriorityBase,
    LienPriorityEnum,
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
    Mismopercent,
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
from ..urla import AssetType, LiabilityType, LoanProgram, Occupancy, OwnStatus, Urla


def borrower_residence(urla: Urla) -> Residences:
    address = urla.address
    residence = Residence(
        address=Address(
            address_line_text=Mismostring(value=address.street_address),
            city_name=Mismostring(value=address.city),
            postal_code=Mismocode(value=address.zip_code),
            state_code=Mismocode(value=address.state),
        ),
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
    urla_inc = urla.income
    employer = Employer(
        legal_entity=LegalEntity(
            legal_entity_detail=LegalEntityDetail(
                full_name=Mismostring(value=urla_inc.employer_name)
            )
        ),
        employment=Employment(
            employment_start_date=Mismodate(
                value=urla_inc.start_date.strftime("%Y-%m-%d")
            ),
            employment_status_type=EmploymentStatusEnum(
                value=EmploymentStatusBase.CURRENT
            ),
            employment_classification_type=EmploymentClassificationEnum(
                value=EmploymentClassificationBase.PRIMARY
            ),
            employment_position_description=Mismostring(value=urla_inc.position or ""),
        ),
    )
    employers = Employers(employer=[employer])

    return employers


def borrower_income(urla: Urla) -> CurrentIncome:
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
    urla_bwr = urla.borrower

    borrower = Borrower(
        borrower_detail=BorrowerDetail(
            borrower_birth_date=Mismodate(
                value=urla_bwr.date_of_birth.strftime("%Y-%m-%d")
            )
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
                    value=borrower.phone_number
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
            ),
        ),
        roles=Roles(role=[borrower_role(urla)]),
    )

    return Parties(party=[party])


def asset_type(at: AssetType) -> AssetEnum:
    value = None
    match at:
        case AssetType.Checking:
            value = AssetBase.CHECKING_ACCOUNT
        case AssetType.Retirement:
            value = AssetBase.RETIREMENT_FUND
        case AssetType.Savings:
            value = AssetBase.SAVINGS_ACCOUNT

    return AssetEnum(value=value)


def borrower_assets(urla: Urla) -> Assets:
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
    sp = urla.subject_property

    collateral = Collateral(
        subject_property=Property(
            address=Address(
                address_line_text=Mismostring(value=sp.street_address)
                if sp.street_address
                else None,
                city_name=Mismostring(value=sp.city) if sp.city else None,
                state_code=Mismocode(value=sp.state) if sp.state else None,
                postal_code=Mismocode(value=sp.zip_code) if sp.zip_code else None,
            ),
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
            ),
        )
    )

    return Collaterals(collateral=[collateral])


def liability_type(lt: LiabilityType) -> LiabilityEnum:
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


def borrower_liabilities(urla: Urla) -> Liabilities:
    liability_list = [
        Liability(
            sequence_number=i + 1,
            label=f"LIABILITY_{i + 1}",
            liability_detail=LiabilityDetail(
                liability_exclusion_indicator=Mismoindicator(value=False),
                liability_monthly_payment_amount=Mismoamount(value=l.monthly_amount),
                liability_payoff_status_indicator=Mismoindicator(value=False),
                liability_remaining_term_months_count=Mismocount(
                    value=l.months_remaining
                )
                if l.months_remaining
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
    value = None

    match lp:
        case LoanProgram.Fha:
            value = MortgageBase.FHA
        case _:
            value = MortgageBase.CONVENTIONAL

    return MortgageEnum(value=value)


def borrower_loans(urla: Urla) -> Loans:
    l_info = urla.loan
    loan = Loan(
        loan_role_type=LoanRoleBase.SUBJECT_LOAN,
        label="LOAN_1",
        amortization=Amortization(
            amortization_rule=AmortizationRule(
                amortization_type=AmortizationEnum(value=AmortizationBase.FIXED),
                loan_amortization_period_count=Mismocount(
                    value=l_info.loan_term_months
                ),
                loan_amortization_period_type=LoanAmortizationPeriodEnum(
                    value=LoanAmortizationPeriodBase.MONTH
                ),
            )
        ),
        housing_expenses=HousingExpenses(
            housing_expense=[
                HousingExpense(
                    housing_expense_payment_amount=None,
                    housing_expense_timing_type=HousingExpenseTimingEnum(
                        value=HousingExpenseTimingBase.PROPOSED
                    ),
                    housing_expense_type=HousingExpenseEnum(
                        value=HousingExpenseBase.FIRST_MORTGAGE_PRINCIPAL_AND_INTEREST
                    ),
                )
            ]
        ),
        loan_detail=LoanDetail(
            borrower_count=Mismocount(value=1),
            balloon_indicator=Mismoindicator(value=False),
            buydown_temporary_subsidy_funding_indicator=Mismoindicator(value=False),
            construction_loan_indicator=Mismoindicator(value=False),
            interest_only_indicator=Mismoindicator(value=False),
            negative_amortization_indicator=Mismoindicator(value=False),
            prepayment_penalty_indicator=Mismoindicator(value=False),
            total_mortgaged_properties_count=Mismocount(value=1),
        ),
        terms_of_loan=TermsOfLoan(
            base_loan_amount=Mismoamount(value=l_info.loan_amount),
            lien_priority_type=LienPriorityEnum(value=LienPriorityBase.FIRST_LIEN),
            loan_purpose_type=LoanPurposeEnum(
                value=LoanPurposeBase.PURCHASE,
            ),
            mortgage_type=mortgage_type(l_info.loan_program),
            note_rate_percent=Mismopercent(value=Decimal("7.00")),
        ),
    )

    return Loans(loan=[loan])


from lxml import etree  # ty: ignore
from xsdata.formats.dataclass.serializers.tree import TreeSerializer

MISMO_NS = "http://www.mismo.org/residential/2009/schemas"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def to_xml(urla: Urla):
    deal = Deal(
        assets=borrower_assets(urla),
        collaterals=borrower_collateral(urla),
        liabilities=borrower_liabilities(urla),
        loans=borrower_loans(urla),
        parties=borrower_parties(urla),
    )

    root = Message(deal_sets=DealSets(deal_set=[DealSet(deals=Deals(deal=[deal]))]))

    # config = SerializerConfig(indent="  ")
    # context = XmlContext()
    # serializer = XmlSerializer(context=context, config=config)

    tree = TreeSerializer().render(root, ns_map={None: MISMO_NS})

    for el in [e for e in tree.iter() if e.get(XSI_NIL) == "true"]:
        el.getparent().remove(el)

    etree.cleanup_namespaces(tree)
    out = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")

    return out
