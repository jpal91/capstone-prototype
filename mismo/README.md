# mismo

The data model for the supported subset of the URLA (Form 1003) and its
mapping to and from MISMO v3.4 (Build 324) XML. `core` uses it to finalize a
draft into the XML a lender receives.

```python
from mismo import Urla, from_xml, to_xml, validate

urla = Urla.model_validate(draft)   # a complete pre-application
xml = to_xml(urla)                  # MISMO v3.4 MESSAGE, UTF-8 bytes
validate(xml)                       # DU wrapper schema (FR-03); raises SchemaValidationError
assert from_xml(xml) == urla        # the round trip (FR-04)
```

`from_xml` reads the single-borrower subset that `to_xml` emits. Anything
outside it (a co-borrower, a gift of cash, a VA loan, self-employment income)
raises `UnsupportedError` rather than being mapped to the nearest value; see
L-03 and L-04 in [`docs/requirements.md`](../docs/requirements.md).

## Getting the schema

The MISMO schema is license-restricted, so neither it nor the code generated
from it is in this repository. Importing `mismo` without the generated
bindings fails with a message pointing here.

1. Accept the license and download the MISMO v3.4 Residential Reference Model:
   https://www.mismo.org/standards-resources/license-form/version-3-4-residential-reference-model
2. Unpack it into `mismo/schema/`, so that this file exists:
   `mismo/schema/ReferenceModel_v3.4.0_B324/Combined/MISMO_3.4.0_B324.xsd`
3. Put Fannie Mae's DU schema files (`DU_Wrapper_3.4.0_B324.xsd` and the
   ULAD/DU extension schemas) in
   `mismo/schema/ReferenceModel_v3.4.0_B324/Fannie Mae DU Schema Files updated 080825/`.
4. From `prototype/`:

   ```sh
   just gen-schema     # bindings -> mismo/src/mismo/generated/ (gitignored)
   just stage-schema   # DU wrapper and what it includes -> mismo/schema/staged/
   ```

Both recipes stop with an error if the files they need are missing.
`validate` reads `mismo/schema/staged/DU_Wrapper_3.4.0_B324.xsd`; set
`MISMO_SCHEMA` to use a staged copy elsewhere (e.g., in a container).
`mismo/schema/` is gitignored, and so is every `*.xsd`. Don't commit the
schema or the generated code, and don't push an image built from them to a
public registry.

Bindings are generated from the base Reference Model; the DU wrapper is used
only to validate emitted XML (FR-03). [ADR 0001](../docs/adr/0001-mismo-schema.md)
explains why.

## Tests

From `prototype/mismo/`:

```sh
uv run pytest
```

The tests use synthetic data only (`tests/synthetic.py`). If Fannie Mae's DU
Specification test cases are unpacked in `mismo/schema/DU Specification Test
Case Suite October 2026/`, `test_from_xml.py` also checks that each one is
rejected for the right reason; otherwise that test is skipped. The
validation tests are skipped when the schema has not been staged.
