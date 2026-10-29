# ADR 0003: Pull distribution with per-lender credentials and a uniform 404

- Status: accepted
- Date: 2026-10-20 (decided), 2026-10-21 (implemented in `core`)
- Requirements: FR-07, FR-09, NFR-03, NFR-04, L-01
- Paper: §5.4, §5.5, §6.1, §6.4

## Context

Once the borrower grants a lender access (ADR 0002), the application has to
reach that lender, and only that lender, for as long as the grant allows. The
lender is a separate organization with its own systems: `core` can't trust
anything it says without authenticating it, and a lender shouldn't be able to
learn anything about other lenders' grants.

## Decision

1. **Pull, not push.** A grant sends nothing. The lender fetches the
   application when it wants it, with `GET /lender/grants/{id}/application`,
   which returns the version's exact stored bytes and an `X-Content-SHA256`
   header (FR-07). The grant is checked at that moment.
2. **Each lender has its own credentials** (NFR-03): a client ID and secret,
   sent with HTTP Basic. `core` stores only the secret's SHA-256 and compares
   in constant time (`hmac.compare_digest`). An unknown client ID and a wrong
   secret get the same 401.
3. **Lenders discover grants by asking.** `GET /lender/grants` lists the
   lender's own active grants (ID, expiry, and the version's hash), standing in
   for the FR-09 notification, which is not built. A notification, if added,
   would only say that a grant exists; it would never carry application data.
4. **Every denial looks the same.** A fetch for another lender's grant, a
   revoked or expired grant, or a grant ID that doesn't exist all get the same
   404 response as an unknown path (`{"detail": "Not Found"}`). The audit log
   records the actual reason (`other_lender`, `revoked`, `expired`, or
   `not_found`) in a `fetch_denied` entry (NFR-04). The route returns the 404
   instead of raising it, because raising would roll back the transaction and,
   with it, that audit entry.
5. **Fetch and revoke are ordered.** The fetch reads the grant row
   `FOR SHARE`, so a revoke that arrives at the same moment waits for the
   fetch to finish (or the fetch waits for the revoke). The audit log then
   records them in the order they happened.
6. **Bad credentials are not audited.** Without valid credentials there is no
   lender to attribute the attempt to.

## Alternatives rejected

- **Push** (`core` sends the XML to the lender when the borrower grants
  access): the data leaves as soon as the grant is made, whether or not the
  lender ever uses it, so revocation would almost always come too late. Push
  also needs an endpoint at every lender and retry logic in `core`. With pull,
  nothing leaves until the lender asks, and a grant revoked before then
  discloses nothing.
- **A full OAuth 2.0 authorization-code or FAPI flow**, as in Open Banking:
  there, the third party starts the flow and the user approves it. Here, the
  borrower starts the share and the lender only collects, so the
  authorization-code flow's redirect and approval steps don't fit. This
  remains the path to production: FAPI-grade client authentication
  (`private_key_jwt` or mutual TLS) in place of shared secrets (§10.3).
- **Distinct responses for each denial** (403 for another lender's grant, 410
  for a revoked one): a lender could then probe grant IDs and learn which
  exist and who holds them. The uniform 404 reveals nothing; the borrower and
  an auditor still see the real reason in the log.
- **Hashing lender secrets with a password hash (Argon2id, as borrower
  passwords are):** a slow hash protects low-entropy secrets that people
  choose. Lender secrets are meant to be generated, high-entropy values, for
  which a fast hash is enough. The demo secrets are random five-word
  passphrases (about 79 bits); a real deployment would generate longer ones,
  and the argument depends on that.

## Consequences

- A lender that has fetched an application keeps its copy after the grant is
  revoked or expires (L-01). Pull limits what leaves, not what happens to it
  afterwards.
- HTTP Basic sends the secret with every request, so it needs TLS. The
  prototype runs only on localhost over HTTP; TLS and secret rotation are
  deferred (§6.4).
- Failed logins are neither audited nor rate-limited.
- Lenders must poll `GET /lender/grants` until a notification exists (FR-09,
  cut line).
