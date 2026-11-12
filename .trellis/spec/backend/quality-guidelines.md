# Backend Quality Guidelines

## Scope / Trigger

Use these checks for `apps/api` changes, including request models, provider
adapters, SQLite migrations, the advice runner and dependency updates. The
configuration is in `apps/api/pyproject.toml`; browser compatibility is captured
in `apps/api/contracts/openapi.json`.

## Commands

Run from `apps/api` with Python 3.12+ and `uv`:

```sh
uv sync --frozen --extra test --extra lint
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra test --extra lint python -m pytest -q
uv run --frozen --extra lint ruff check src tests
uv lock --check --offline
```

Disk-store tests exercise the real 3 GiB free-space reserve. If `/tmp` is a
smaller tmpfs, set `TMPDIR` to a private disposable directory on a filesystem
with sufficient free space; do not weaken the storage reserve to pass tests.

Ruff checks `E`, `F`, `I`, `UP` and `B`, targets Python 3.12 and uses a
100-character line limit. No Python type checker is configured; do not report
type checking as passed. Install the declared lint extra when Ruff is missing;
an unavailable local wheel cache is not a successful lint result. Dependency
downloads are separate from the tests' offline provider behavior.

## Contracts

- Tests use disposable SQLite paths and injected providers, `httpx.MockTransport`
  or fake SDK event streams. Never load `.env.local`, inherit provider credentials
  for a model turn, or contact a paid endpoint from an automated check.
- Use `create_app(settings, database, image_provider=..., tag_search=...,
  advice_runner=...)` for explicit test dependencies. Fixtures use fake HTTPS
  origins so the Secure cookie and mutation `Origin` checks remain exercised.
- Keep the checked-in OpenAPI snapshot deterministic and credential-free.
  A public request/response change requires intentional snapshot review and a
  check of `apps/web/src/api.ts`; never regenerate a snapshot merely to hide
  an unexplained test failure.
- Apply local lint fixes without changing behavior. Public interfaces, runtime
  isolation guarantees and deployment topology require a task/design decision.
- Express route dependencies as `Annotated[UserInfo, Depends(require_user)]`
  rather than a `Depends(...)` default value. This satisfies Ruff `B008`
  without global suppression; the OpenAPI snapshot guards the public contract.
- Keep prompts, access tokens, sessions and upstream errors out of diagnostic
  output. Assertions may use sentinel credentials to prove their absence.

## Validation & Error Matrix

| Check | Required result |
| --- | --- |
| Existing suite and behavior regressions | All tests pass against fakes and disposable data |
| Ruff over `src tests` | No violations; do not skip tests from lint scope |
| Frozen dependency install / lock check | Declared dependencies and lock agree |
| OpenAPI regression | Exact reviewed snapshot match, typed errors, no configured secrets |
| Missing lint tool | Install declared extra or record an incomplete quality gate |
| No configured Python type checker | Record not configured, not passed |
| Actual NovelAI/Codex behavior | Separate runtime integration gate; fake tests do not establish it |

## Good / Base / Bad Cases

- Good: change pagination bounds and add API tests for valid boundaries,
  rejected queries and owner-scoped page contents; then review the snapshot.
- Base: `test_openapi_contract_matches_snapshot_without_database_or_provider_calls`
  builds the schema with sentinel settings and verifies it creates no SQLite
  file and exposes no credentials.
- Bad: replace a fake with a configured paid provider to make a test pass,
  suppress a Ruff rule globally for a local fix, or claim a successful real
  model turn based on mocked events.

## Tests Required

Add regressions for a changed contract or a concrete behavior bug; use the
existing suite for mechanical fixes instead of adding implementation-mirroring
tests. The current test modules own these boundaries:

| Module | Assertion points |
| --- | --- |
| `tests/test_auth.py` | Token digests, cookie flags, revocation, origin checks, private DB/backup modes |
| `tests/test_generations.py` | Owner isolation, seed resolution, pagination, deletion, bounded jobs, injected memory cache, restart/backup |
| `tests/test_image_retention.py` | Private durable images, expiry, capacity reservations, owners and filesystem safety |
| `tests/test_purged_images.py` | Stable per-image memory/disk removal, pending retry, owner/current-set scope, restore/render races and schema13 restart |
| `tests/test_style_plan.py` | Exact tokenizer/decimal/Cartesian parity, neutral weights, Unicode and plan limits |
| `tests/test_style_runs.py` | Durable claim/Stop/recovery, failed continuation, seed, idempotency, fairness and migration3 |
| `tests/test_prompt_sections.py` | Strict hidden editor metadata, effective projection, history/backup/restart, frozen run metadata and legacy omission |
| `tests/test_prompt_snapshots.py` | Private immutable snapshot CRUD, owner/Origin/no-store, pagination/idempotency, schema4 migration and backup/restart |
| `tests/test_mcp_images.py` | Schema compatibility, PNG validation, safe errors and no retry of uncertain paid outcomes |
| `tests/test_provider_requests.py` | Exact pre-call arguments, owner isolation, unavailable legacy records, schema5 migration and backup/restart |
| `tests/test_account_balance.py` | Strict Anlas allowlist, read-only MCP/deadline/caps, cache singleflight/cancellation and authenticated no-store route |
| `tests/test_tags.py` | NSFW normalization, deadlines, decoded-size caps, concurrency and validated upstream `Retry-After` |
| `tests/test_advice.py` | Explicit input only, structured output, observed tool rejection and child cleanup |
| `tests/test_api_contract.py` | Deterministic snapshot, documented errors and secret-free schema |

## Wrong vs Correct

- Wrong: leave Ruff unchecked because an offline cache is empty, then mark the
  quality gate complete because pytest passed previously.
- Correct: install `--extra lint`, run Ruff on source and tests, rerun relevant
  checks after fixes, and record exact commands and unresolved runtime gates.
- Wrong: describe `read-only` advice sandboxing as proof that no tool can run.
- Correct: preserve the accepted restriction and observed-event rejection
  contract in [Codex Advice Runtime](./codex-advice-contract.md).
