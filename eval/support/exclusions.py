"""Finding SSN and HMDA names (NFR-01, NFR-02) without false matches.

Names are compared word by word, because a substring search would flag harmless
names: "ssn" is in "businessName", and "race" is in "GracePeriod".
"""

import re
from collections.abc import Iterable

from lxml import etree  # ty: ignore

from support.xml import MISMO_NS

WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+")
SSN_WORDS = {"ssn", "itin", "tin", "taxpayer"}
HMDA_WORDS = {"hmda", "ethnicity", "race", "gender", "sex", "monitoring"}


def words(name: str) -> set[str]:
    """`TaxpayerIdentifierValue` -> {"taxpayer", "identifier", "value"}."""
    return {word.lower() for word in WORD.findall(name)}


def excluded(names: Iterable[str]) -> set[str]:
    return {name for name in names if words(name) & (SSN_WORDS | HMDA_WORDS)}


def disallowed_elements(doc: etree._Element) -> set[str]:
    """Elements for excluded data, and any extension or non-MISMO elements."""
    found = set()
    for element in doc.iter(etree.Element):
        name = etree.QName(element)
        if (
            name.namespace != MISMO_NS
            or "extension" in words(name.localname)
            or excluded([name.localname])
        ):
            found.add(element.tag)
    return found
