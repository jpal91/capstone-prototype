from ..generated import (
    Borrower,
    BorrowerDetail,
    ContactPoint,
    ContactPointEmail,
    ContactPoints,
    ContactPointTelephone,
    CurrentIncome,
    CurrentIncomeItem,
    CurrentIncomeItems,
    # Deal,
    # Deals,
    # DealSet,
    # DealSets,
    Individual,
    Mismodate,
    # Message,
    MismonumericString,
    Mismostring,
    Mismovalue,
    Name,
    # Parties,
    Party,
    Role,
    Roles,
)
from ..urla import Urla

## TODO LEFT OFF HERE


def borrower_role(urla: Urla) -> Role:
    urla_bwr = urla.borrower
    role = Role(sequence_number=1, label="BORROWER_1")

    borrower = role.borrower = Borrower(
        borrower_detail=BorrowerDetail(
            borrower_birth_date=Mismodate(
                value=urla_bwr.date_of_birth.strftime("%Y-%m-%d")
            )
        )
    )

    urla_inc = urla.income

    ci_items = CurrentIncomeItems()
    income = CurrentIncome(current_income_items=ci_items)

    ci_item = CurrentIncomeItem()

    return role


def borrower_party(urla: Urla) -> Party:
    party = Party()
    borrower = urla.borrower

    individual = party.individual = Individual()
    individual.contact_points = ContactPoints()
    contact_points = individual.contact_points.contact_point

    if borrower.email:
        cp_email = ContactPoint(
            contact_point_email=ContactPointEmail(
                contact_point_email_value=Mismovalue(value=borrower.email)
            )
        )
        contact_points.append(cp_email)

    if borrower.phone_number:
        cp_phone = ContactPoint(
            contact_point_telephone=ContactPointTelephone(
                contact_point_telephone_value=MismonumericString(
                    value=borrower.phone_number
                )
            )
        )
        contact_points.append(cp_phone)

    individual.name = Name(
        first_name=Mismostring(value=borrower.first_name),
        last_name=Mismostring(value=borrower.last_name),
    )

    party.roles = Roles()

    return party
