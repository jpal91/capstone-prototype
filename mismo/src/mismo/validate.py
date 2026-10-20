"""Validate MISMO XML against Fannie Mae's DU wrapper schema (FR-03).

The DU wrapper is the MISMO v3.4 schema with the ULAD and DU extensions
added, i.e., what a lender's pipeline would check. ``just stage-schema`` puts
it and the files it includes in ``mismo/schema/staged/``; set
``MISMO_SCHEMA`` to use a copy somewhere else (e.g., in a container).

The schema is licensed, not committed, so a missing copy is an error that
says how to get it rather than a silent pass. It is loaded once and reused.
"""

import os
from functools import cache
from pathlib import Path

from lxml import etree  # ty: ignore

SCHEMA_ENV = "MISMO_SCHEMA"
DEFAULT_SCHEMA = (
    Path(__file__).parents[2] / "schema" / "staged" / "DU_Wrapper_3.4.0_B324.xsd"
)

# Emitted XML has no DTD or entities, so refuse them rather than resolve them.
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


class SchemaValidationError(ValueError):
    """The XML is not valid against the DU wrapper schema."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def schema_path() -> Path:
    """Where the DU wrapper is read from: ``MISMO_SCHEMA``, or the staged copy."""
    return Path(os.environ.get(SCHEMA_ENV, DEFAULT_SCHEMA))


@cache
def load_schema(path: Path) -> etree.XMLSchema:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Run `just stage-schema`, or set {SCHEMA_ENV} "
            "to the staged DU_Wrapper_3.4.0_B324.xsd (see mismo/README.md)."
        )
    return etree.XMLSchema(etree.parse(str(path), PARSER))


def validate(xml: bytes) -> None:
    """Raise ``SchemaValidationError`` unless ``xml`` is valid (FR-03).

    The error lists every problem the schema reports, with its line number.
    XML that is not well-formed raises the same error.
    """
    schema = load_schema(schema_path())

    try:
        doc = etree.fromstring(xml, PARSER)
    except etree.XMLSyntaxError as e:
        raise SchemaValidationError([f"not well-formed: {e}"]) from None

    if not schema.validate(doc):
        raise SchemaValidationError(
            [f"line {e.line}: {e.message}" for e in schema.error_log]
        )
