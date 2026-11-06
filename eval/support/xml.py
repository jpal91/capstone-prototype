"""Reading XML the services return, independently of the mismo library."""

from lxml import etree  # ty: ignore

MISMO = "{http://www.mismo.org/residential/2009/schemas}"

# Emitted XML has no DTD or entities, so refuse them rather than resolve them.
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
