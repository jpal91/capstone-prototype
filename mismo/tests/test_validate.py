"""Unit tests for ``validate``: emitted XML against the DU wrapper (FR-03).

Every shape of ``to_xml`` output must validate. Skipped when the schema has
not been staged (``just stage-schema``), since it is not in the repository.

These are unit tests; the black-box checks that verify requirements live in
eval/.
"""

from pathlib import Path

import pytest
from synthetic import FULL, application

from mismo import SchemaValidationError, to_xml, validate
from mismo.urla import Urla
from mismo.validate import SCHEMA_ENV, schema_path

pytestmark = pytest.mark.skipif(
    not schema_path().is_file(), reason="DU wrapper schema not staged"
)

MISMO_NS = b'xmlns="http://www.mismo.org/residential/2009/schemas"'


@pytest.mark.parametrize(
    "urla",
    [
        application(0, 0),
        application(1, 0),
        application(0, 1),
        application(3, 2),
        FULL,
    ],
    ids=["minimal", "one-asset", "one-liability", "several", "every-field"],
)
def test_emitted_xml_is_valid(urla: Urla) -> None:
    validate(to_xml(urla))


def test_an_invalid_value_is_reported() -> None:
    # MISMONumericString is digits only; E.164's leading + is not allowed.
    xml = to_xml(FULL).replace(b"5205550100", b"+15205550100")
    with pytest.raises(SchemaValidationError, match="ContactPointTelephoneValue"):
        validate(xml)


def test_an_unknown_element_is_reported() -> None:
    xml = to_xml(application(1, 0)).replace(b"ASSETS>", b"ASSETZ>")
    with pytest.raises(SchemaValidationError, match="ASSETZ"):
        validate(xml)


def test_every_error_carries_a_line_number() -> None:
    xml = to_xml(FULL).replace(b"5205550100", b"+15205550100")
    with pytest.raises(SchemaValidationError) as raised:
        validate(xml)
    assert raised.value.errors
    assert all(error.startswith("line ") for error in raised.value.errors)


def test_xml_that_is_not_well_formed_is_reported() -> None:
    with pytest.raises(SchemaValidationError, match="not well-formed"):
        validate(to_xml(application(0, 0))[:-20])


def test_a_document_in_another_namespace_is_invalid() -> None:
    xml = to_xml(application(0, 0)).replace(MISMO_NS, b'xmlns="urn:example"')
    with pytest.raises(SchemaValidationError):
        validate(xml)


def test_the_schema_location_can_be_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(SCHEMA_ENV, str(schema_path()))
    validate(to_xml(application(0, 0)))

    missing = tmp_path / "DU_Wrapper_3.4.0_B324.xsd"
    monkeypatch.setenv(SCHEMA_ENV, str(missing))
    with pytest.raises(FileNotFoundError, match="just stage-schema"):
        validate(to_xml(application(0, 0)))
