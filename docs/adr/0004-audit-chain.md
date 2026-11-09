# ADR 0004: A hash-chained, append-only audit log in the database

- Status: accepted
- Date: 2026-10-21 (implemented in `core`)
- Requirements: NFR-04, FR-08, L-05, L-06
- Paper: §5.2, §6.2, §6.4

## Context

A borrower who shares an application needs a record of what happened to it:
which versions were finalized, who was given access, who fetched what and
when, and which fetches were refused. For that record to mean anything, an
edit to an earlier entry has to be detectable, including an edit made
directly in the database.

## Decision

1. **One append-only table**, `audit_event`, with an entry for every finalize,
   grant, revoke, fetch, and denied fetch (NFR-04). An entry stores IDs
   (borrower, lender, version, grant) and a small `detail`: the version's
   SHA-256 for a finalize or fetch, the expiry for a grant, the reason for a
   denial. It never stores application data.
2. **Each entry is chained to the previous one.** Its hash is
   `SHA-256(prev_hash + canonical JSON of the entry)`, where the JSON covers
   the sequence number, timestamp, action, IDs, and detail, with sorted keys.
   The first entry's `prev_hash` is 64 zeros. Changing, removing, or reordering
   an earlier entry breaks every hash after it.
3. **One chain, no gaps, no forks.** Appends take a transaction-level advisory
   lock (`pg_advisory_xact_lock`), so sequence numbers are assigned one at a
   time without gaps. `prev_hash` is `UNIQUE`, so two entries can never extend
   the same predecessor.
4. **Written with the action it records.** An entry is added in the same
   transaction as its action, so both commit or neither does.
5. **The database refuses edits.** A trigger blocks `UPDATE`, `DELETE`, and
   `TRUNCATE` on `audit_event` (the same trigger protects `version`).
6. **Verification is a function**, `core.audit.verify_chain`, which
   recomputes every hash and reports the first bad sequence number. There is
   no route for it; `eval/support/audit.py` is a separate verifier, which shares
   only the entry format.
7. **The log is also a data source.** A grant's `lastFetchedAt` is the time of
   its newest `fetch` entry (FR-08), so the borrower sees the same record an
   auditor would.

## Alternatives rejected

- **A plain log table (no chain):** anyone with write access to the database
  could change an entry without leaving a trace.
- **Relying on the trigger alone:** the table's owner can disable a trigger,
  and `core` connects as that owner (L-06). The trigger stops accidental and
  casual edits; the chain is what detects deliberate ones.
- **Signed entries or signed receipts for borrowers and lenders:** these would
  let parties outside `core` prove what happened, but need key management and
  distribution. Future work (§10.3).
- **A Merkle tree or transparency log (RFC 9162):** gives efficient proofs
  that an entry is included and that the log only grew, which matters when
  outside parties check the log. A linear chain checked end to end is enough
  for the prototype. Future work (§10.3).
- **Application log files:** easy to edit or lose, and not written in the same
  transaction as the action, so a log line could describe something that was
  rolled back.

## Consequences

- The chain can't detect deletion of the newest entries, or a complete
  rewrite of the chain with fresh hashes, by someone with write access to the
  database (L-05). Anchoring the latest hash outside the database would close
  that gap; it is future work.
- `core` can disable the trigger as the table owner (L-06). A production
  deployment would connect as a role limited to `INSERT` and `SELECT` on the
  table.
- All appends are serialized by the lock, which limits write throughput. That
  is fine for a demonstration.
- Entries link borrowers and lenders by ID, so the log itself is personal
  data, even though it holds no application content.
