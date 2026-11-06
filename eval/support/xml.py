"""Reading XML the services return, independently of the mismo library."""

from typing import Any

from lxml import etree  # ty: ignore

from support.clients import BorrowerClient

MISMO_NS = "http://www.mismo.org/residential/2009/schemas"
MISMO = f"{{{MISMO_NS}}}"
NAMESPACES = {"m": MISMO_NS}  # for xpath(), where m: means this namespace

# Emitted XML has no DTD or entities, so refuse them rather than resolve them.
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def fetch_finalized(alice: BorrowerClient, draft: dict[str, Any]) -> etree._Element:
    """Finalize `draft` and parse the XML core then serves for that version."""
    version = alice.must_finalize(draft)
    xml = alice.version_xml(version["id"])
    assert xml.status_code == 200
    return etree.fromstring(xml.content, PARSER)
