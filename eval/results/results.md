# Results

Run 2026-11-06T21:43:19+00:00. 159 tests: 159 passed, 0 failed, 0 skipped, 0 errors.

## Results by table

### Functional Requirements

| ID | Result | Tests passed | Requirement |
|---|---|---|---|
| FR-01 | passed | 2/2 | The borrower can create, edit, and save a draft covering the supported URLA... |
| FR-02 | passed | 4/4 | Finalizing a draft produces an immutable version: MISMO v3.4 XML stored with... |
| FR-03 | passed | 3/3 | Every finalized version validates against Fannie Mae's DU wrapper schema for... |
| FR-04 | passed | 44/44 | Emitted XML round-trips: parsing it back yields the same field values as the... |
| FR-05 | passed | 7/7 | The borrower can grant a specific lender access to a specific version, with... |
| FR-06 | passed | 5/5 | The borrower can revoke any grant independently; other grants are unaffected. |
| FR-07 | passed | 11/11 | A lender can fetch an application only with a grant that is its own, not... |
| FR-08 | passed | 5/5 | The borrower can see every grant's status and when each lender last fetched. |
| FR-09 | not tested | 0/0 | When a grant is created, the lender receives a notification that carries no... |
| FR-10 | not tested | 0/0 | A demo lender view shows what each mock lender has received and its current... |

### Non-functional and Security Requirements

| ID | Result | Tests passed | Requirement |
|---|---|---|---|
| NFR-01 | passed | 9/9 | The SSN / taxpayer identifier is never collected, stored, or emitted. |
| NFR-02 | passed | 10/10 | HMDA demographic information is not collected. |
| NFR-03 | passed | 9/9 | Each lender authenticates with its own credentials; one lender's credentials... |
| NFR-04 | passed | 18/18 | Every finalize, grant, revoke, fetch, and denied fetch adds an entry to an... |
| NFR-05 | not tested | 0/0 | Stored version XML is encrypted at rest with a key supplied through the... |
| NFR-06 | not tested | 0/0 | All data is synthetic. |
| NFR-07 | passed | 1/1 | The whole system starts with `docker compose up --build` and is removed with... |
| NFR-08 | passed | 37/37 | Every borrower route requires a valid session, and a borrower can read or... |

### Known Limitations to Demonstrate

*A result of `passed` means the limitation was demonstrated*

| ID | Result | Tests passed | Limitation |
|---|---|---|---|
| L-01 | passed | 3/3 | Revocation stops future fetches but cannot take back a copy a lender already... |
| L-02 | passed | 5/5 | Output is valid against the DU schema but not DU-submittable: the SSN is... |
| L-03 | not tested | 0/0 | Single borrower only; no co-borrower. |
| L-04 | not tested | 0/0 | Employment income is recorded as a wage (`CURRENT_INCOME_ITEM`, `IncomeType`... |
| L-05 | passed | 11/11 | The audit hash chain detects alteration, deletion, or reordering of earlier... |
| L-06 | passed | 1/1 | `core` connects to Postgres as the owner of the audit table (a superuser in... |

## Tests that did not pass

None

## Not tested by `eval/`

| ID | Intended Check |
|---|---|
| FR-09 | Notification received; payload has no application fields |
| FR-10 | Screenshot (Ch. 7); not automated. `mock-lender`'s `/api` routes let `eval/` check what each lender holds |
| NFR-05 | Raw database column is not readable XML; fetch still returns the original bytes |
| NFR-06 | Review; not automated |
| L-03 | Scope statement; not automated |
| L-04 | `mismo`'s tests, not `eval/`: `from_xml` rejects DU test case DI-CL01 with a clear error; reading DI-C01 keeps its Base item and drops its six other income items |
