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
| FR-01 | The borrower can create, edit, and save a draft covering the supported URLA subset: borrower information, current address, employment and income, assets, liabilities, and property and loan information. | §4.1 | `portal` /borrower, `core` drafts | Scenario creates and updates a draft | Core |
| FR-02 | Finalizing a draft produces an immutable version: MISMO v3.4 XML stored with its SHA-256 hash. Editing afterward creates a new version and never changes an existing one. | §2.2, §6.2 | `core` versions, `mismo` mapper | Finalize twice; first version's bytes and hash unchanged | Core |
| FR-03 | Every finalized version validates against Fannie Mae's DU wrapper schema for MISMO v3.4 (Build 324), so a lender receives the format its systems already import. | §2.2 | `mismo` validation | XSD validation of every emitted file against the staged DU wrapper | Core |
| FR-04 | Emitted XML round-trips: parsing it back yields the same field values as the source draft. | §2.2, §5.2 | `mismo` mapper + bindings | Parse emitted XML, compare to draft; Fannie Mae's DU test case DI-C01 also reads and re-emits | Core |
| FR-05 | The borrower can grant a specific lender access to a specific version, with an expiry. | §2.3.2, §2.3.4 | `core` grants, `portal` consent screen | Grant A and B, not C; C is denied | Core |
| FR-06 | The borrower can revoke any grant independently; other grants are unaffected. | §2.3.2, §2.3.4 | `core` grants | Revoke A; A denied, B still allowed | Core |
| FR-07 | A lender can fetch an application only with a grant that is its own, not revoked, and not expired. The response is exactly the bound version's bytes (hash matches). | §2.3.2, §5.4, §6.2 | `core` lender API | Consent matrix: own/other lender × active/revoked/expired; hash check on success; every denial returns the same 404, and its audit entry records the reason | Core |
| FR-08 | The borrower can see every grant's status and when each lender last fetched. | §2.3.4 | `core` grants + audit, `portal` | Scenario reads grant list after fetches | Core |
| FR-09 | When a grant is created, the lender receives a notification that carries no application data. | §5.4 | `core` → `mock-lender` webhook | Notification received; payload has no application fields | Cut line |
| FR-10 | A demo lender view shows what each mock lender has received and its current access status. | §7.2 | `portal` /lender, `mock-lender` | Screenshot (Ch. 7); not automated | Cut line |

## Non-functional and security requirements

| ID | Requirement | Source | Satisfied by | Verified by | Priority |
|---|---|---|---|---|---|
| NFR-01 | The SSN / taxpayer identifier is never collected, stored, or emitted. | §4.4, §6.2, §6.3 | Form scope, data model | No such field in the draft API; no taxpayer identifier in any emitted XML | Core |
| NFR-02 | HMDA demographic information is not collected. | §4.4, §6.3 | Form scope | No such fields in the draft API or emitted XML | Core |
| NFR-03 | Each lender authenticates with its own credentials; one lender's credentials cannot read another lender's grants. | §6.1 | `core` lender auth | Lender B uses its credentials on Lender A's grant → denied | Core |
| NFR-04 | Every finalize, grant, revoke, fetch, and denied fetch adds an entry to an append-only audit log in which each entry stores the previous entry's hash; the chain verifies end to end. | §6.2, §6.4 | `core` audit | Run scenario, check entry count per action, verify chain; tamper with one row → verification fails | Core |
| NFR-05 | Stored version XML is encrypted at rest with a key supplied through the environment. | §6.4 | `core` storage | Raw database column is not readable XML; fetch still returns the original bytes | Cut line |
| NFR-06 | All data is synthetic. | `AGENTS.md` guardrails | `seed` | Review; not automated | Core |
| NFR-07 | The whole system starts with `docker compose up --build` and is removed with `docker compose down -v`; `eval/` runs in the same environment. | §3.3, §7 | `compose.yaml` | The eval run itself | Core |
| NFR-08 | Every borrower route requires a valid session, and a borrower can read or change only their own draft, versions, and grants. | §6.1 | `core` borrower auth | No session → 401; borrower B on A's draft, versions, or grants → 404 | Core |

## Known limitations to demonstrate (not requirements — expected outcomes)

These are things the design intentionally does *not* do. `eval/` should show each one happening so the paper can report it honestly (§6.1, §8.4, §10.1).

| ID | Limitation | Source | Shown by |
|---|---|---|---|
| L-01 | Revocation stops future fetches but cannot take back a copy a lender already fetched. | §5.4, §6.1 | After revoking A, `mock-lender` still holds A's earlier copy |
| L-02 | Output is valid against the DU schema but not DU-submittable: the SSN is absent, and no ULAD/DU extension data (e.g., HMDA demographics, which NFR-02 excludes) is emitted. | §4.4, §10.1 | Note alongside FR-03 results |
| L-03 | Single borrower only; no co-borrower. | §10.1 | Scope statement; not automated |
| L-04 | Employment income is recorded as a wage (`CURRENT_INCOME_ITEM`, `IncomeType` Base). A self-employed borrower with a 25% or greater ownership share reports a single monthly income or loss (`EmploymentMonthlyIncomeAmount`) on the URLA instead, which the subset cannot represent; importing such a file is rejected rather than relabeled as a wage. Only base pay is imported: other income items in a lender's file (overtime, bonus, dividends, ...) are ignored, so the imported income can be lower than the file states. | §4.1, §10.1 | `from_xml` rejects DU test case DI-CL01 with a clear error; reading DI-C01 keeps its Base item and drops its six other income items |
| L-05 | The audit hash chain detects alteration, deletion, or reordering of earlier entries, but not deletion of the newest entries or a complete rewrite of the chain by someone with write access to the database. Anchoring the chain head outside the database (or a Merkle/transparency log) is future work. | §6.4, §10.1 | Truncate the newest entries, or rewrite the chain with fresh hashes → verification still passes |
| L-06 | `core` connects to Postgres as the owner of the audit table (a superuser in the dev image), so a compromised `core` could disable the append-only trigger and rewrite the log; the trigger only stops accidental or casual edits, and the hash chain is what detects tampering. A production deployment would connect as a role limited to `INSERT` and `SELECT` on the audit table. | §6.4 | The NFR-04 tamper test disables the trigger as `core`'s own database user before editing a row |
