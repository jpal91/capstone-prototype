# mock-lender

Stands in for the lenders' own systems (Next.js 16, React 19, daisyUI on
Tailwind, Drizzle on Postgres). Each demo lender checks `core` for the
applications borrowers have shared with it, fetches them with its own
credentials, verifies their SHA-256, and keeps its own copies. It is a
separate trust domain from `core`: it has its own database and reaches `core`
only over HTTP, through the lender API, like any lender would (ADR 0003).

It acts for two lenders, `lender-a` and `lender-b`. Lender C has no mock
lender; `eval/` uses it as a lender with no grant.

This is a research prototype that uses synthetic data only (NFR-06).

## Pages and routes

| Route                                                 | What it does                                                                                                                      | Requirements       |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `/`                                                   | Pick a lender                                                                                                                     | FR-10              |
| `/lenders/[clientId]`                                 | The lender's shared applications (access status, last fetch and its result), "Check for applications", Fetch, and received copies | FR-07, FR-10, L-01 |
| `/lenders/[clientId]/copies/[grantId]/xml`            | The stored copy's exact bytes, with `X-Content-SHA256`                                                                            | FR-07, L-01        |
| `POST /api/lenders/[clientId]/sync`                   | Check `core` for grants. 200 with counts, 502 if `core` fails                                                                     | for `eval/`        |
| `POST /api/lenders/[clientId]/grants/[grantId]/fetch` | Fetch one application. 200 verified, 409 access ended, 404 unknown grant, 502 otherwise                                           | for `eval/`        |
| `GET /api/lenders/[clientId]/copies`                  | The lender's stored copies (without the XML)                                                                                      | for `eval/`        |

An unknown lender is a 404 on every route.

## How it works

- **Check for applications** calls `GET /lender/grants`, standing in for the
  notification that isn't built (FR-09). New grants are recorded; grants no
  longer listed are marked "access ended". `core` doesn't say whether a grant
  was revoked or expired, by design, so neither does the lender.
- **Fetch** calls `GET /lender/grants/{id}/application`. A copy is stored only
  if the body's SHA-256 matches both the `X-Content-SHA256` header and the
  hash listed with the grant. A 404 (any denial looks the same) marks access
  as ended.
- **Copies are never deleted.** Revoking a grant stops future fetches; it
  can't take back a copy the lender already holds (L-01).

## Run

From `prototype/`, with Docker only (NFR-07):

```sh
docker compose up --build   # mock-lender on http://localhost:3001
docker compose down -v      # remove everything, including both databases
```

The `lender` database and role are created by `db/init.sql`, which Postgres
runs only on an empty data volume. The tables are created by the migrations in
`drizzle/`, which the app applies at startup (`instrumentation-node.ts`).

## Develop

Run the database and `core` in Docker and the app natively:

```sh
docker compose up -d db core   # from prototype/
pnpm install                   # from prototype/ (the pnpm workspace root)
pnpm dev                       # from mock-lender/; http://localhost:3001
```

`LENDER_A_SECRET` and `LENDER_B_SECRET` must be set, e.g. in
`mock-lender/.env` (gitignored), with the defaults from `compose.yml`.
`DATABASE_URL` and `CORE_URL` default to the local compose ports. The
`mock-lender` container also uses port 3001, so don't run both.

After changing `app/lib/db/schema.ts`, run `pnpm exec drizzle-kit generate` and
commit the new folder in `drizzle/`; it is applied on the next start.

Checks: `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm format:check` (or
`pnpm format` to fix).

The `core` client types in `app/lib/core/` are generated, as in the portal:
regenerate them from `prototype/` with `just gen-api`.

## Layout

- `app/lib/`: server-only code: the `core` client with each lender's Basic
  credentials (`core/client.ts`), the lender list (`lenders.ts`), sync and
  fetch (`grants.ts`), reads for the pages (`data.ts`), and the database
  (`db/`).
- `app/actions/`: Server Actions for the Sync and Fetch buttons.
- `app/api/`: JSON routes for `eval/`, calling the same functions.
- `app/components/`: UI.

## Limitations

Deliberate shortcuts for the demo:

- **No staff login.** Anyone who can open the app can act as either lender. A
  real lender's system would authenticate its own staff.
- **The `/api` routes are unauthenticated** and, unlike Server Actions, have
  no CSRF (Origin) check: a web page open in the same browser could make a
  lender sync or fetch. That only makes the lender do what it is already
  allowed to do, and `core` audits it.
- **One process holds both lenders' `core` secrets**, as a hosted
  origination system serving several lenders would. A compromise of this app
  exposes both.
- **The database separation is logical.** `mock-lender` connects only as the
  `lender` role, but `core` connects as a superuser in the dev image (L-06),
  so a compromised `core` could read the lender database.
- Like the portal, it runs over plain HTTP on localhost; HTTP Basic would need
  TLS anywhere else.
