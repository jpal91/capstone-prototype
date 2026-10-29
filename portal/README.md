# portal

The borrower's web UI (Next.js 16, React 19, daisyUI on Tailwind). A borrower
fills in a pre-application, finalizes it into immutable MISMO XML versions,
and shares a version with a lender for a fixed time, with revocation at any
time. All data lives in `core`; the portal calls it server-side only and
holds no data of its own.

This is a research prototype that uses synthetic data only (NFR-06). It is
a _pre-application_: no Social Security number or HMDA demographic
information is collected (NFR-01, NFR-02).

## Pages

| Route                         | What it does                                                                                                                                                       | Requirements        |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| `/login`                      | Sign in with a demo account (`alice`, `bob`)                                                                                                                       | NFR-08              |
| `/borrower`                   | Draft summary; finalized versions with who they're shared with, until when, and when they were last fetched; share and revoke; view or download each version's XML | FR-05, FR-06, FR-08 |
| `/borrower/application`       | The pre-application form: save, or save and finalize                                                                                                               | FR-01, FR-02        |
| `/borrower/versions/[id]/xml` | The exact stored XML bytes, with `X-Content-SHA256`                                                                                                                | FR-02               |

The lender view (`/lender`, FR-10) is not built yet.

## Run

From `prototype/`, with Docker only (NFR-07):

```sh
docker compose up --build   # portal on http://localhost:3000
docker compose down -v      # remove everything, including the database
```

The demo passwords are the defaults in `compose.yml`.

## Develop

Run the database and `core` in Docker and the portal natively:

```sh
docker compose up -d db core   # from prototype/; core on 127.0.0.1:8000
pnpm install                   # from prototype/ (the pnpm workspace root)
pnpm dev                       # from portal/; http://localhost:3000
```

`docker compose up` without service names also starts the portal container on
port 3000, which then clashes with `pnpm dev`. Set `CORE_URL` if `core` isn't
on `http://127.0.0.1:8000`.

Checks: `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm format:check` (or
`pnpm format` to fix).

### The `core` client

`app/lib/core/schema.ts` and `openapi.json` are generated from `core`'s
OpenAPI spec and committed (the portal image builds with Node only). After
changing `core`'s routes or models, regenerate them from `prototype/` with
`just gen-api`, which also exports each enum's values as an array
(`loanPurposeValues`, …) for validation and select options.

## Layout

- `app/lib/`: server-only code: the typed `core` client (`core/client.ts`),
  the session cookie (`session.ts`), and data functions (`utils.ts`).
- `app/actions/`: Server Actions (login and logout, save and finalize the
  draft, grant and revoke). Every export of a `"use server"` file is a public
  POST endpoint, so helpers live in other modules.
- `app/components/`: UI; `draft/` holds the form's sections and fields.

## Notes

- **Session:** the httpOnly, Secure, `SameSite=Lax` cookie holds `core`'s
  opaque session token; the portal has no session store. `core` checks the
  token and ownership on every call; a 401 sends the user to `/login`.
- **Form saves:** inputs are named by draft path (`assets.0.amount`); the
  action rebuilds the nested draft and validates it leniently, with
  completeness checked by `core` at finalize. Errors from either come back
  keyed by the same names and show next to their fields.
- **Times** are rendered on the server, so in the container they are in UTC;
  the zone is always shown.
