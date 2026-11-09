# Requirements — Portable Mortgage Pre-Application Prototype

**Status:** first draft (week 1). Expected to change, but only on purpose.

This is the single list of requirement IDs used by the paper (Ch. 4 defines them, Ch. 7 shows them, Ch. 8 reports results), the code, and the `eval/` suite (each scenario is tagged with the ID it verifies). Section numbers in "Source" refer to `paper_outline.md` at the repository root.

**Rules**

- IDs are permanent. Never renumber; if a requirement is dropped, mark it **Retired** and leave the row.
- Every row is either verified by `eval/` or reported in the paper as unverified.
- Priority **Core** = must ship for Ch. 7–8 to work. **Cut line** = first to drop if the schedule slips (drop in this order: FR-09 notification, FR-10 lender view, NFR-05 encryption at rest).

## Functional requirements

| ID | Requirement | Source | Satisfied by | Verified by | Priority |
|---|---|---|---|---|---|
| FR-01 | The borrower can create, edit, and save a draft covering the supported URLA subset: borrower information, current address, employment and income, assets, liabilities, and property and loan information. | §4.1 | `core` `GET`/`PUT /draft`; `portal` `/borrower/application` | Scenario creates and updates a draft | Core |
| FR-02 | Finalizing a draft produces an immutable version: MISMO v3.4 XML stored with its SHA-256 hash. Editing afterward creates a new version and never changes an existing one. | §2.2, §6.2 | `core` `POST /draft/finalize`, `version` table (append-only trigger), `GET /versions/{id}/xml`; `mismo.to_xml`; ADR 0001 | Finalize twice; first version's bytes and hash unchanged; the database refuses changes to a stored version | Core |
| FR-03 | Every finalized version validates against Fannie Mae's DU wrapper schema for MISMO v3.4 (Build 324), so a lender receives the format its systems already import. | §2.2 | `mismo.validate` (DU wrapper), run at every finalize; ADR 0001 | `eval/` validates a required-fields draft and an every-field draft against the staged DU wrapper, with a control that invalid XML is rejected; `core` itself validates every version at finalize | Core |
| FR-04 | Emitted XML round-trips: parsing it back yields the same field values as the source draft. | §2.2, §5.2 | `mismo.to_xml` / `from_xml`, one table per enum in `mismo/convert/mappings.py`; ADR 0001 | `eval/` checks each draft field is at its expected MISMO path in the emitted XML. `mismo`'s tests cover parsing back with `from_xml`, and Fannie Mae's DU test case DI-C01 reading and re-emitting | Core |
| FR-05 | The borrower can grant a specific lender access to a specific version, with an expiry. | §2.3.2, §2.3.4 | `core` `POST /grants`; `portal` share form on the latest version card; ADR 0002 | Grant A and B, not C; C is denied | Core |
| FR-06 | The borrower can revoke any grant independently; other grants are unaffected. | §2.3.2, §2.3.4 | `core` `POST /grants/{id}/revoke`; `portal` Revoke button; ADR 0002 | Revoke A; A denied, B still allowed | Core |
| FR-07 | A lender can fetch an application only with a grant that is its own, not revoked, and not expired. The response is exactly the bound version's bytes (hash matches). | §2.3.2, §5.4, §6.2 | `core` `GET /lender/grants/{id}/application`; ADR 0003 | Consent matrix: own/other lender × active/revoked/expired; hash check on success; every denial returns the same 404, and its audit entry records the reason | Core |
| FR-08 | The borrower can see every grant's status and when each lender last fetched. | §2.3.4 | `core` `GET /grants` (`lastFetchedAt` from the audit log); `portal` `/borrower` | Scenario reads grant list after fetches and denials; `lastFetchedAt` matches the audit log's fetch time | Core |
| FR-09 | When a grant is created, the lender receives a notification that carries no application data. | §5.4 | Not built. `core` `GET /lender/grants` stands in (lenders poll; `mock-lender`'s "Check for applications"); ADR 0003 | Notification received; payload has no application fields | Cut line |
| FR-10 | A demo lender view shows what each mock lender has received and its current access status. | §7.2 | `mock-lender` `/lenders/[clientId]` (a separate app with its own database, not a portal page) | Screenshot (Ch. 7); not automated. `mock-lender`'s `/api` routes let `eval/` check what each lender holds | Cut line |

## Non-functional and security requirements

| ID | Requirement | Source | Satisfied by | Verified by | Priority |
|---|---|---|---|---|---|
| NFR-01 | The SSN / taxpayer identifier is never collected, stored, or emitted. | §4.4, §6.2, §6.3 | Draft and URLA models in `mismo/urla.py` have no taxpayer identifier field | Draft API rejects such fields with a 422 and doesn't define them; no such name in `core`'s columns, stored drafts, stored versions, or emitted XML. Checks names, not what's typed into a free-text field | Core |
| NFR-02 | HMDA demographic information is not collected. | §4.4, §6.3 | No HMDA fields in `mismo/urla.py`; no ULAD/DU extension elements emitted (ADR 0001) | Draft API rejects such fields with a 422 and doesn't define them; no such name in `core`'s columns, stored drafts, stored versions, or emitted XML, and no extension elements | Core |
| NFR-03 | Each lender authenticates with its own credentials; one lender's credentials cannot read another lender's grants. | §6.1 | `core.auth.current_lender` (HTTP Basic, per-lender secret stored as SHA-256); ADR 0003 | Lender B uses its credentials on Lender A's grant → denied; a wrong secret, another lender's secret, an unknown client, or a borrower session → 401 | Core |
| NFR-04 | Every finalize, grant, revoke, fetch, and denied fetch adds an entry to an append-only audit log in which each entry stores the previous entry's hash; the chain verifies end to end. | §6.2, §6.4 | `core.audit` (`append`, `verify_chain`), `audit_event` triggers; ADR 0004 | Run scenario, check entry count per action, verify chain; tamper with one row → verification fails | Core |
| NFR-05 | Stored version XML is encrypted at rest with a key supplied through the environment. | §6.4 | Not built | Raw database column is not readable XML; fetch still returns the original bytes | Cut line |
| NFR-06 | All data is synthetic. | `AGENTS.md` guardrails | `core-seed` (`seed.py`); `portal` notice on `/` and `/login`; `mock-lender` notice on `/` | Review; not automated | Core |
| NFR-07 | The whole system starts with `docker compose up --build` and is removed with `docker compose down -v`; `eval/` runs in the same environment. | §3.3, §7 | `compose.yml` (`db`, `seed`, `core`, `portal`, `mock-lender`, and `eval` under its profile) | `just eval-fresh` runs the suite in compose on a rebuilt, empty stack, and a test confirms it's in a container on the compose network. That test can't see how the stack was started, so Ch. 8 reports the run itself | Core |
| NFR-08 | Every borrower route requires a valid session, and a borrower can read or change only their own draft, versions, and grants. | §6.1 | `core.auth.current_session` / `current_borrower`, borrower filters in `core/services.py`; `portal` session cookie | No session, an unknown token, or lender credentials → 401 on every borrower route; borrower B on A's versions or grants → the same 404 as an unused ID. `/draft` takes no ID, so B can't address A's draft; a scenario shows the two stay separate | Core |

## Known limitations to demonstrate (not requirements — expected outcomes)

These are things the design intentionally does *not* do. `eval/` should show each one happening so the paper can report it honestly (§6.1, §8.4, §10.1).

| ID | Limitation | Source | Shown by |
|---|---|---|---|
| L-01 | Revocation stops future fetches but cannot take back a copy a lender already fetched. | §5.4, §6.1 | After revoking A, `mock-lender` still holds A's earlier copy (`GET /api/lenders/lender-a/copies`), while A's next fetch gets the uniform 404 |
| L-02 | Output is valid against the DU schema but not DU-submittable: the SSN is absent, and no ULAD/DU extension data (e.g., HMDA demographics, which NFR-02 excludes) is emitted. | §4.4, §10.1 | `eval/` shows the XML is valid and has no SSN, HMDA, or extension elements. It is never submitted to DU; report this alongside the FR-03 results |
| L-03 | Single borrower only; no co-borrower. | §10.1 | Scope statement; not automated |
| L-04 | Employment income is recorded as a wage (`CURRENT_INCOME_ITEM`, `IncomeType` Base). A self-employed borrower with a 25% or greater ownership share reports a single monthly income or loss (`EmploymentMonthlyIncomeAmount`) on the URLA instead, which the subset cannot represent; importing such a file is rejected rather than relabeled as a wage. Only base pay is imported: other income items in a lender's file (overtime, bonus, dividends, ...) are ignored, so the imported income can be lower than the file states. | §4.1, §10.1 | `mismo`'s tests, not `eval/`: `from_xml` rejects DU test case DI-CL01 with a clear error; reading DI-C01 keeps its Base item and drops its six other income items |
| L-05 | The audit hash chain detects alteration, deletion, or reordering of earlier entries, but not deletion of the newest entries or a complete rewrite of the chain by someone with write access to the database. Anchoring the chain head outside the database (or a Merkle/transparency log) is future work. | §6.4, §10.1 | Truncate the newest entries, or rewrite the chain with fresh hashes → verification still passes |
| L-06 | `core` connects to Postgres as the owner of the audit table (a superuser in the dev image), so a compromised `core` could disable the append-only trigger and rewrite the log; the trigger only stops accidental or casual edits, and the hash chain is what detects tampering. A production deployment would connect as a role limited to `INSERT` and `SELECT` on the audit table. | §6.4 | The NFR-04 tamper test disables the trigger as `core`'s own database user before editing a row |
