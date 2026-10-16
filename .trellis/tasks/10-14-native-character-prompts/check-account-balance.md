# Independent check: Image-service Anlas balance

Date: 2026-10-16. Active task: `10-14-native-character-prompts`.

## Findings (fixed)

None. No product source or test corrections were necessary.

## Findings (not fixed)

No blocking or nonblocking product defects found in the affected source.

The live-probe helper verifies the deployed read-only MCP balance adapter using
the running service's existing private configuration. It does **not** perform
an authenticated browser-route GET. Describe that evidence accurately:
authenticated route behavior is covered by fake integration tests, while the
activation helper separately verifies loopback/public unauthenticated 401 and
no-store. No live helper or provider query was run by this checker.

Parent owns final specification sync, clean build, matched-source staging,
publication and runtime evidence. The frontend workspace contract's AppStore
ownership list/link should reflect the new balance store, alongside the new
cross-layer account-balance contract. This is documentation coordination,
not an unresolved product decision.

## Scope reviewed

- `account_balance.py`: strict four-field frozen response, safe exact sum,
  fixed public failures, off-thread provider query, five-second monotonic
  cache, shared concurrent success/failure, shielded waiter cancellation and
  shutdown ownership without stale-success fallback.
- `mcp_account.py`: separate read-only initialize/notification/discovery/
  get_subscription sequence, strict protocol/request IDs and verified no-arg
  schema, canonical structured data with deliberate single-text fallback,
  allowlisted counts, bounded JSON/SSE/compression, whole-operation cooperative
  deadline, no redirects/retries/generation tool and generic diagnostics.
- `app.py`, account tests and reviewed additive OpenAPI: auth before provider,
  no-store, no constructor/schema provider/database effects, no migration,
  independent errors and retained experiment/manager shutdown order.
- `api.ts`, `balance-store.ts`, `AccountBalance.tsx`, `store.ts`, `App.tsx`,
  `styles.css`: exact safe wire validation, true zero, unavailable/stale values
  and original fetch time, responsive header/details/refresh, idempotent entry,
  visible 30-second polling, non-postponed 5.5-second activity timer, retained
  follow-up intent across an older read, hidden-tab deferral, ordinary terminal
  and experiment-progress callback composition, failed-logout remount and
  session/reset/disposal cleanup.
- Existing paid image adapter and server experiment scheduler were not
  changed; account observation adds no generation/advice POST and cannot
  modify submission certainty, paid retry behavior or experiment continuation.

## Release helper review

Read-only source review of these parent-prepared helpers found no release
blockers; none was executed by this checker:

- `/tmp/nai-account-balance-build.py`: explicit environment-free inputs,
  source symlink rejection, locked offline dependency install, production
  base path and source/artifact hashes.
- `/tmp/nai-account-balance-stage.py`: exact working/committed/build web input
  sets and hashes, matched API source set, no credential/config loading,
  root-owned staged release, offline frozen dependencies, pinned CLI check,
  exact side-effect-free OpenAPI and disposable schema4/SQLite checks.
- `/tmp/nai-account-balance-activate.py`: unchanged baseline pointers/PID,
  zero-active-work checks, exclusive private verified online backup,
  schema4 continuity without migration/DB restore, unchanged configuration,
  API-first readiness/OpenAPI/auth checks, manifest/PNG byte and original
  expiry preservation, public new/old asset hashes and compatible recovery.
- `/tmp/nai-account-balance-live-probe.py`: read-only adapter verification
  with existing runtime credentials, normalized fields/recent timestamp and
  safe report only; no account values or third-party stderr printed.

## Verification

All checks used repository source, disposable SQLite and fake providers. The
backend commands below ran from `apps/api` with a clean environment containing
only PATH, HOME, UV_NO_ENV_FILE=1 and UV_PYTHON_DOWNLOADS=never. They loaded no
`.env.local` or provider credentials.

```sh
uv --no-config sync --frozen --offline --extra test --extra lint
uv --no-config run --frozen --offline --extra test --extra lint python -m pytest -q
uv --no-config run --frozen --offline --extra lint ruff check src tests
uv --no-config lock --check --offline
```

- Backend tests: **639 passed** in 32.88 seconds. Two existing third-party
  Starlette/TestClient deprecation warnings; no failures.
- Backend lint: **pass**, Ruff over source and tests.
- Frozen dependency/lock checks: **pass**.
- OpenAPI: **pass**, exact tested snapshot; reviewed changes add only the
  balance route/schema and typed errors. No secret/config values.
- Frontend lint and TypeScript: **pass**, `npm run lint` from `apps/web`
  executes ESLint and `tsc --noEmit`.
- `git diff --check`: **pass**.
- Python type-check: **not configured** in this project.

No frontend/helper automated tests, browser automation, paid generation,
advice turn, production mutation, commit or deployment was performed by this
checker. A fresh final build and actual publication/runtime verification are
parent release steps, not claims of this source gate. Actual per-request
billing and generated image appearance remain outside the verified balance
contract.
