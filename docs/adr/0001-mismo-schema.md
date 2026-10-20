# ADR 0001: MISMO v3.4 XML, bindings from the base schema, validation against the DU wrapper

- Status: accepted
- Date: 2026-10-16 (decided), 2026-10-20 (implemented in `mismo`)
- Requirements: FR-02, FR-03, FR-04, NFR-01, NFR-02, L-02, L-03, L-04
- Paper: §2.2, §5.5

## Context

A lender should be able to import the borrower's application without
remapping it. Fannie Mae's Desktop Underwriter takes the Uniform Loan
Application Dataset (ULAD) as MISMO v3.4 XML, and loan origination systems
export applications in that format. The MISMO schema is license-restricted, so
neither it nor code generated from it can be committed to this public
repository.

Fannie Mae publishes a DU wrapper schema (`DU_Wrapper_3.4.0_B324.xsd`) that
redefines MISMO's `*_EXTENSION` types to add the ULAD and DU extension
elements. xsdata cannot generate bindings from it: the extension schemas import
the MISMO data types without a namespace, and generation stops on an unknown
group reference.

## Decision

1. **Format:** MISMO v3.4, Build 324, as XML.
2. **Bindings:** generate xsdata dataclasses from the base Reference Model
   (the single-file `Combined/MISMO_3.4.0_B324.xsd`) with `just gen-schema`.
   The generated package is gitignored.
3. **Validation:** validate every emitted file against the DU wrapper, staged
   with its includes by `just stage-schema`. This is the schema the receiving
   system checks, so "valid" in FR-03 means valid where it matters.
4. **No extension elements:** the supported URLA subset fits entirely in the
   base model, so `to_xml` emits no ULAD or DU extensions. HMDA demographics,
   the main extension content, are not collected (NFR-02).
5. **One mapping, two directions:** each URLA enum maps to exactly one MISMO
   value through a table in `mismo/convert/mappings.py`. `to_xml` reads the
   tables forward and `from_xml` in reverse, so the two cannot drift apart
   (FR-04).
6. **Reject, don't relabel:** `from_xml` raises `UnsupportedError` for
   anything outside the subset (a co-borrower, a gift of cash, a VA loan,
   self-employment income) instead of mapping it to the nearest URLA value.
   One exception: income items other than base pay are ignored rather than
   rejected, so a lender's file with overtime or dividends still imports, with
   lower income (L-04).

## Alternatives rejected

- **MISMO JSON (v3.5 and later):** ULAD, DU, and the major loan origination
  systems' exports are pinned to v3.4 XML, so a lender would have to convert
  it. Future work (§10.3).
- **iLAD 2.5:** MISMO's industry loan application dataset, at Candidate
  Recommendation status. DU consumes ULAD on v3.4, not iLAD, so targeting
  ULAD's base keeps the output importable today.
- **Bindings generated from the DU wrapper:** not possible with xsdata (see
  Context). Hand-patching the extension schemas would mean shipping modified
  copies of licensed files.
- **Validating against the base schema only:** the same files pass both, but
  the DU wrapper is what a lender's pipeline would apply, so it is the stronger
  check at no extra cost.
- **Pydantic bindings (`xsdata-pydantic`):** the generated module is very
  large, and input is already validated by the URLA models in `urla.py` and by
  the XSD. Plain dataclasses avoid a second validation layer.
- **Mapping out-of-subset values to the nearest URLA value (or an `Other`
  member):** it would silently change the borrower's stated finances, and an
  `Other` value accepted from XML would also be accepted from the borrower
  and need its own MISMO mapping.

## Consequences

- The output is XSD-valid but not DU-submittable: it has no SSN (NFR-01) and
  no ULAD/DU extension data (L-02).
- Self-employed borrowers with a 25% or greater ownership share, and
  co-borrowers, are outside the subset (L-03, L-04).
- Anyone building or running the prototype must download the schema
  themselves (`mismo/README.md`). Images built from it contain generated MISMO
  code and must not be pushed to a public registry.
- `from_xml` reads by position, which holds for `to_xml` output and for the
  DU test cases, but not necessarily for files from other systems.
- Of Fannie Mae's 18 DU test cases, one (DI-C01) is within the subset apart
  from its extra income items, and reads; the rest are rejected, each for
  something outside the subset. DI-C01 needed three more URLA 2a account types
  (certificate of deposit, mutual fund, trust account), which were added.
