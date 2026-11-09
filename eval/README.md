# eval

The black-box scenario suite for the prototype. Each test is tagged with the
requirement IDs it verifies (`docs/requirements.md`), and a run writes a pass/fail
table by ID, which is what the paper's Ch. 8 reports. It tests the running services
and never imports `core` or `mismo`, so it can't inherit their bugs.

It uses synthetic data only (NFR-06).

## Run

From `prototype/`, with the stack's images buildable (see `mismo/README.md` for
the license-restricted schema):

```sh
just eval-fresh       # the official run: wipes the stack, rebuilds, runs everything
just eval             # the same suite against the stack as it is
just eval -k consent  # part of it; pytest arguments replace --report
```

Without `just`, Docker alone is enough:

```sh
docker compose up -d --build --wait
docker compose --profile eval run --rm --build eval
```

The container runs as uid 1000 unless `EVAL_UID` and `EVAL_GID` say otherwise, and
has to be able to write to `eval/results/`.

To run it natively against the published ports (`CORE_URL`, `MOCK_LENDER_URL`,
`CORE_DATABASE_URL`, and `MISMO_SCHEMA` have local defaults), export the demo
credentials from `compose.yml`, stage the schema with `just stage-schema`, then:

```sh
cd eval && uv run pytest
```

## Results

`--report` writes `results/results.md` and `results/results.json`, only when the
whole run finished. The committed copies come from `just eval-fresh`.

- A requirement's result is its worst test: `failed`, then `error`, `skipped`,
  `passed`. `failed` means checked and wrong; `error` means it couldn't be checked.
- Every ID appears. One with no tests is `not tested`, and its "Verified by" text
  says where its evidence is instead.
- The run stops, with no report, if a service, the database, or the DU schema is
  missing.

## Layout

| File                              | Covers                                     |
| --------------------------------- | ------------------------------------------ |
| `scenarios/test_draft.py`         | FR-01                                      |
| `scenarios/test_versions.py`      | FR-02                                      |
| `scenarios/test_schema.py`        | FR-03, L-02                                |
| `scenarios/test_mapping.py`       | FR-04                                      |
| `scenarios/test_consent.py`       | FR-05 to FR-08, NFR-03                     |
| `scenarios/test_exclusions.py`    | NFR-01, NFR-02, L-02                       |
| `scenarios/test_isolation.py`     | NFR-08                                     |
| `scenarios/test_lender_copies.py` | L-01, FR-06                                |
| `scenarios/test_audit.py`         | NFR-04, L-05, L-06, FR-02, FR-05 to FR-08  |
| `scenarios/test_environment.py`   | NFR-07                                     |
| `support/report.py`               | The pytest plugin that writes the report   |
| `support/audit.py`                | The audit chain verifier, separate from `core.audit` |
| `support/clients.py`              | HTTP clients for borrowers and lenders     |

Every test needs a `@pytest.mark.req("ID")` with an ID from `requirements.md`, or
the run stops before it starts.

## How it looks inside

Everything goes over HTTP except the audit checks and the "stored" half of NFR-01
and NFR-02, which read `core`'s database because no route exposes them. The audit
tamper tests connect as `core`'s own role, disable the append-only trigger, change
rows, and roll back, so the real log is never altered. Tests must run one at a time,
which is the default, because those locks would block `core`.

## A run changes the stack

- It adds versions, grants, and audit entries for Alice and Bob, and copies to the
  mock lender, so `just docker-restart` before a demo.
- It replaces any open portal session for Alice or Bob, because it logs in as them.
- `test_each_action_adds_one_entry` expects exactly its own audit entries, so using
  the portal or mock lender during a run can fail it.

## What the results don't show

- **FR-03** is shown on two drafts, not every possible one. `core` also validates
  each version when it's finalized.
- **FR-04** here is a value-at-its-path check. The round trip through `from_xml`
  is in `mismo`'s tests, which keeps the licensed bindings out of this suite.
- **NFR-01, NFR-02** check names, not values: nothing stops someone typing an SSN
  into a free-text field. Only `core`'s database is read, not the mock lender's.
- **NFR-04:** a 401 from wrong credentials adds no audit entry; only requests from a
  real lender are recorded. The verifier's JSON key names and timestamp format came
  from `core`, because ADR 0004 doesn't give them, so a mistake there would be in both.
- **NFR-07:** see the note in `test_environment.py`.
- **L-01** is true of the mock lender by design. What makes it true of lenders in
  general is the architecture (ADR 0003).
- Denials are compared by content, not timing, and revoking and fetching at the same
  moment isn't tried.
