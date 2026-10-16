from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from ..generated import (
    ContactPoint,
    ContactPointEmail,
    ContactPoints,
    ContactPointTelephone,
    Deal,
    Deals,
    DealSet,
    DealSets,
    Individual,
    Message,
    MismonumericString,
    Mismostring,
    Mismovalue,
    Name,
    Parties,
    Party,
)
from ..urla import Urla

# from .utils import borrower_party


def to_xml(urla: Urla) -> bytes:
    # TODO: Change to error
    assert urla.borrower is not None

    root = Message()

    deal_sets = root.deal_sets = DealSets()
    deal_set = DealSet()
    deal_sets.deal_set.append(deal_set)

    deals = deal_set.deals = Deals()
    deal = Deal()
    deals.deal.append(deal)

    parties = deal.parties = Parties()
    party = Party()
    parties.party.append(party)

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

    config = SerializerConfig(indent="  ")
    context = XmlContext()
    serializer = XmlSerializer(context=context, config=config)

    out = serializer.render(root)

    return out.encode()


def validate(xml: bytes) -> None:
    pass


# def from_xml(xml: bytes) -> Urla:
#     return Urla()
