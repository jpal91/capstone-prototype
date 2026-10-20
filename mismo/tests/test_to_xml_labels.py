"""Unit tests for the xlink labels and relationships ``to_xml`` emits.

The builders label elements and ``relationships`` links them by those labels.
The XSD does not check that the two agree, so a mismatch would still
validate but leave a lender unable to tell whose asset or debt is whose.
These tests catch that.

These are unit tests; the black-box checks that verify requirements live in
eval/.
"""

import pytest
from lxml import etree  # ty: ignore
from synthetic import application

from mismo.convert import to_xml
from mismo.urla import Urla

XLINK = "{http://www.w3.org/1999/xlink}"
ARCROLE_PREFIX = "urn:fdc:mismo.org:2009:residential/"


def parse(urla: Urla) -> etree._Element:
    return etree.fromstring(to_xml(urla))


def labelled(doc: etree._Element) -> dict[str, etree._Element]:
    """Every element with an ``xlink:label``, keyed by label."""
    return {e.get(f"{XLINK}label"): e for e in doc.iter() if e.get(f"{XLINK}label")}


def links(doc: etree._Element) -> list[tuple[str, str, str]]:
    """Each ``RELATIONSHIP`` as (from, to, arcrole without its URN prefix)."""
    return [
        (
            r.get(f"{XLINK}from"),
            r.get(f"{XLINK}to"),
            r.get(f"{XLINK}arcrole").removeprefix(ARCROLE_PREFIX),
        )
        for r in doc.iter("{*}RELATIONSHIP")
    ]


SHAPES = pytest.mark.parametrize(
    ("assets", "liabilities"), [(0, 0), (1, 0), (0, 1), (3, 2)]
)


@SHAPES
def test_labels_are_unique(assets: int, liabilities: int) -> None:
    doc = parse(application(assets, liabilities))
    labels = [e.get(f"{XLINK}label") for e in doc.iter() if e.get(f"{XLINK}label")]
    assert len(labels) == len(set(labels))


@SHAPES
def test_every_relationship_points_at_a_label(assets: int, liabilities: int) -> None:
    doc = parse(application(assets, liabilities))
    labels = labelled(doc)
    for src, dst, _ in links(doc):
        assert src in labels, f"xlink:from={src} has no matching label"
        assert dst in labels, f"xlink:to={dst} has no matching label"


@SHAPES
def test_arcrole_matches_the_linked_elements(assets: int, liabilities: int) -> None:
    # An arcrole names its ends: ASSET_IsAssociatedWith_ROLE runs from an
    # ASSET element to a ROLE element.
    doc = parse(application(assets, liabilities))
    labels = labelled(doc)
    for src, dst, arcrole in links(doc):
        from_tag, _, to_tag = arcrole.partition("_IsAssociatedWith_")
        assert etree.QName(labels[src]).localname == from_tag
        assert etree.QName(labels[dst]).localname == to_tag


@SHAPES
def test_each_asset_and_liability_is_linked_to_the_borrower(
    assets: int, liabilities: int
) -> None:
    doc = parse(application(assets, liabilities))
    labels = labelled(doc)
    to_borrower = [src for src, dst, _ in links(doc) if dst == "BORROWER_1"]
    expected = [
        label
        for label, e in labels.items()
        if etree.QName(e).localname in ("ASSET", "LIABILITY")
    ]
    assert sorted(to_borrower) == sorted(expected)
    assert len(expected) == assets + liabilities


def test_income_is_linked_to_the_employer() -> None:
    doc = parse(application(0, 0))
    assert links(doc) == [
        (
            "CURRENT_INCOME_ITEM_1",
            "EMPLOYER_1",
            "CURRENT_INCOME_ITEM_IsAssociatedWith_EMPLOYER",
        )
    ]


@SHAPES
def test_relationship_sequence_numbers_count_from_one(
    assets: int, liabilities: int
) -> None:
    doc = parse(application(assets, liabilities))
    numbers = [int(r.get("SequenceNumber")) for r in doc.iter("{*}RELATIONSHIP")]
    assert numbers == list(range(1, assets + liabilities + 2))
