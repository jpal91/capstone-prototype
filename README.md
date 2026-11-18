# One Application: prototype

A research prototype for a senior capstone paper, *One Application: A Study in an
Efficient Mortgage Application Process*. It tests whether the mortgage industry's
existing data standard, MISMO v3.4, can carry a pre-application that the borrower
controls.

A borrower fills in one pre-application. The system converts it to MISMO v3.4 XML,
validates it against Fannie Mae's Desktop Underwriter (DU) schema, and stores it as a
version that cannot be changed. The borrower then grants individual lenders access to
that version. Each grant has an expiry and can be revoked on its own. Lenders pull the
file with their own credentials, and every action is recorded in a hash-chained audit
log.

**This is a demonstration, not a deployable system.**
- All data are synthetic.
- It has not been used by real borrowers or lenders, and its usability has not been
  evaluated.
- It does not collect the Social Security number or HMDA demographic information, so
  what a lender receives is a pre-application. The file is valid against the DU schema,
  but DU would not accept it as submitted.

## Components

| Directory      | What it is                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------- |
| `mismo/`       | Python library: the supported URLA fields, the mapping to and from MISMO XML, and schema validation |
| `core/`        | FastAPI service: drafts, immutable versions, grants, the lender API, and the audit log         |
| `portal/`      | Next.js borrower UI, on http://localhost:3000                                                   |
| `mock-lender/` | Next.js app that stands in for two lenders' own systems, with its own database, on http://localhost:3001 |
| `eval/`        | Black-box scenario suite that checks each requirement over HTTP                                |
| `docs/`        | Requirements (`requirements.md`) and architecture decision records (`adr/`)                    |

PostgreSQL 18 holds `core`'s data and, in a separate database, the mock lender's. Docker
Compose runs everything.

## Before you start: the MISMO schema

The MISMO schema is license-restricted, so neither it nor the code generated from it is
in this repository. The images cannot be built without it. To get it:

1. Accept MISMO's license and download the v3.4 Residential Reference Model (Build 324).
2. Get Fannie Mae's DU schema files for MISMO v3.4 (`DU_Wrapper_3.4.0_B324.xsd` and
   the ULAD/DU extension schemas).
3. Put both where [`mismo/README.md`](mismo/README.md#getting-the-schema) says.

The schema folder is gitignored. **Images built from it contain licensed material, so
never push them to a public registry.**

## Requirements

- Docker with Compose v2
- [`just`](https://github.com/casey/just) (optional; every recipe below has a plain
  Docker equivalent)
- For development outside Docker only: [`uv`](https://docs.astral.sh/uv/) and
  [`pnpm`](https://pnpm.io/)

## Run the demo

```sh
docker compose up -d --build --wait
```

Then open the borrower portal at http://localhost:3000 and the mock lender at
http://localhost:3001. The seeded borrowers are `alice` and `bob`. Their demo passwords
are the defaults in `compose.yml`, which are public on purpose and are only for this
local demo. All ports are bound to `127.0.0.1`.

To stop it and delete all of its data:

```sh
docker compose down -v
```

## Reproduce the evaluation

```sh
just eval-fresh
```

This deletes the stack's data, rebuilds every image on an empty database, and runs the
scenario suite. It writes a pass/fail table by requirement to
`eval/results/results.md` and `results.json`.

Without `just`:

```sh
docker compose down -v
docker compose up -d --build --wait
docker compose --profile eval run --rm --build eval
```

The committed results come from the run of 2026-11-06: 159 tests, all passed. The
results by requirement, what each test checks, and what the results do not show are
in [`eval/README.md`](eval/README.md).

## Documentation

- [`docs/requirements.md`](docs/requirements.md): the requirements (FR-01 to FR-10,
  NFR-01 to NFR-08), the known limitations (L-01 to L-06), and how each is verified
- [`docs/adr/`](docs/adr/): why the design uses the base MISMO schema, whole-application
  grants, pull distribution, and a hash-chained audit log
- The READMEs in `mismo/`, `portal/`, `mock-lender/`, and `eval/` cover each
  component's details and development commands

## Known limitations

These are covered in full in `docs/requirements.md`.
- Revoking a grant stops future retrieval. It cannot take back a copy a lender already
  holds.
- Only a single borrower with wage income is supported.
- The audit chain does not detect deletion of the newest entries or a full rewrite by
  someone with write access to the database.
- Two requirements were specified but not built: lender notification (FR-09) and
  encryption of stored versions (NFR-05).
- There is no TLS. Services are reachable only from the local machine.

## License

The code in this repository is released under the [MIT License](LICENSE). The license
does not cover the MISMO schema or Fannie Mae's DU schema files, which are not in this
repository and stay under their owners' terms. It also does not cover the bindings or
Docker images generated from those files.
