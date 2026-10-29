# Build Schedule — 8 Weeks

**This is a plan, not a rule.** It exists to put the riskiest work first and leave a working system at the end of every week. Move things around as reality dictates; just keep the cut order below so Ch. 7–8 always have something to stand on.

Requirement IDs refer to `requirements.md` in this folder.

| Week | Goal | Done when | Requirements |
|---|---|---|---|
| 1 | Skeleton | Repo layout, `compose.yml` with every service stubbed, uv workspace, Next.js scaffold; requirement list reviewed | NFR-07 (stubbed) |
| 2 | `mismo` library (riskiest piece) | Bindings generated from the local XSD, mapper covers the supported URLA subset, emitted XML validates and round-trips | FR-03, FR-04, NFR-01, NFR-02 |
| 3 | `core` drafts and versions | Draft API, finalize into an immutable hashed version, borrower sessions, encryption of stored versions | FR-01, FR-02, NFR-05 |
| 4 | `core` consent and audit | Grants (version-bound, expiring, revocable), lender credentials, lender fetch API, hash-chained audit log | FR-05–FR-07, NFR-03, NFR-04 |
| 5 | Portal borrower pages | Form, finalize, grant and revoke, grant status with last-fetch times | FR-01, FR-05, FR-06, FR-08 |
| 6 | `mock-lender` and lender view | Mock lender fetches and keeps its own copies; `/lender` demo view; notification webhook if time allows | FR-09, FR-10, L-01 |
| 7 | `eval/` and demonstration material | Scenario suite runs in compose and writes a pass/fail table by requirement ID; screenshots for Ch. 7 | All |
| 8 | Buffer and freeze | Slipped work, documentation, ADRs, code freeze | — |

## If the schedule slips

Drop in this order:

1. FR-09 — lender notification webhook
2. FR-10 — `/lender` demo view (mock lender logs to the console instead)
3. NFR-05 — encryption at rest (reported as deferred in §6.4)

The consent rules (FR-05 to FR-07), the audit log (NFR-04), and the `eval/` suite are not on the cut list — Ch. 7 and 8 depend on them.
