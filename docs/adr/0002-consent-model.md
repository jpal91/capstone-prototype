# ADR 0002: Whole-application grants, bound to one lender, one version, and an expiry

- Status: accepted
- Date: 2026-10-20 (decided), 2026-10-21 (implemented in `core`), 2026-10-29 (portal consent screen)
- Requirements: FR-05, FR-06, FR-08, NFR-04, NFR-08, L-01
- Paper: §5.3, §5.5, §6.2

## Context

The borrower, not the lender, decides who sees the application, for how
long, and which version of it. That control has to be specific enough to be
meaningful (this lender, this file, until this date) and simple enough that a
borrower can see at a glance who has access and take it away.

A lender quotes on the whole application: income, assets, debts, property,
and loan together. The application also changes over time, while a lender
needs to know exactly which data it was given.

## Decision

1. **Whole-application consent.** A grant gives one lender access to one
   finalized version in full. There is no section- or field-level consent.
2. **Bound to one version.** A grant names a version, and the lender receives
   exactly that version's stored bytes, whose SHA-256 it can check (FR-02,
   FR-07). Later edits create a new version (FR-02); they never reach a lender
   through an existing grant. Sharing the newer data takes a new grant.
3. **Bound to one lender, with an expiry.** `POST /grants` takes `lenderId`,
   `versionId`, and `expiresAt`, which must be in the future. The version must
   belong to the borrower; otherwise the response is a 404, the same as for a
   version that doesn't exist (NFR-08). The portal offers 7, 30, or 90 days,
   and its server computes the time, so the browser's clock never sets it.
4. **Independently revocable, never deleted.** Revoking sets `revoked_at`
   once; other grants, including the same lender's grants for other versions,
   are unaffected (FR-06). A database trigger allows no other change to a
   grant row and refuses deletes, so the grant history stays complete. Revoke
   is idempotent: revoking again returns the grant unchanged and adds no audit
   entry.
5. **One status rule.** A grant's status comes from a single SQL expression,
   evaluated against the database clock: revoked if `revoked_at` is set, else
   expired if `expires_at` has passed, else active. The borrower's grant list,
   the lender's grant list, and the fetch check all use it, so they can't
   disagree.
6. **Several grants per lender are allowed**, for example for two versions,
   or a new grant after an expired one. The portal greys out a lender that
   already has an active grant for the same version.
7. **Every grant and revoke is audited** in the same transaction (NFR-04,
   ADR 0004). The borrower sees each grant's status and the lender's last
   fetch, which is read from the audit log (FR-08).

## Alternatives rejected

- **Section- or field-level consent:** a lender can't quote on a partial
  file, so it would ask for the rest, and the borrower would be choosing
  between sharing everything and not being served. Partial files would also
  need rules for which combinations are meaningful. Minimization is done
  instead by what is never collected (no SSN or HMDA data: NFR-01, NFR-02) and
  by binding each grant to one recipient, one version, and a time limit
  (§6.2).
- **Access to "the application" rather than a version** (the lender always
  sees the latest): every edit would reach every lender with access, whether
  or not the borrower meant to share it, and a lender could not tie its quote
  to the exact data it saw.
- **Open-ended grants (no expiry):** access the borrower forgets about stays
  open indefinitely. An expiry makes the default outcome "access ends".
- **Deleting a grant on revoke:** the borrower and the audit log would lose
  the record that the lender had access and when it last fetched (FR-08).
- **Editable grants (extending an expiry, switching the version):** a grant
  would no longer describe a single decision by the borrower. A new grant
  records the new decision; the old one can be revoked.

## Consequences

- Revocation stops future fetches only. A copy the lender already fetched
  can't be recalled (L-01). The portal says so in the consent text, before
  the borrower shares.
- A lender with access to an older version doesn't see later changes. The
  dashboard warns on such versions when their content differs from the
  latest, and the portal offers sharing on the latest version only.
- Expiry is checked at fetch time against the database clock; nothing runs
  when a grant expires.
- The grant row trigger, like the audit table's, only stops accidental or
  casual edits by `core`'s own database user (L-06).
