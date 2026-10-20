# Check: Advice Configuration Reuse (2026-10-20)

## Findings (fixed)

None. The independent review required no product or test corrections.

## Findings (not fixed)

No blocking issues found. Actual upstream credential validity, selected-model
compatibility, latency and advice/translation quality remain operator
acceptance; the checks deliberately made no real model request.

## Reviewed scope

- `config.py`: optional endpoint/model environment settings preserve absent or
  exactly empty defaults; the shared bounded validators reject unsafe URL or
  whitespace/control forms without echoing values. Direct Settings and runner
  construction use the same validators. Private fields stay out of repr.
- `app.py` / `codex_advice.py`: only a configured key enables the default
  runner. Optional base passes through SDK `base_url`, optional model through
  thread `model`; unset options are omitted. Key login remains stdin-only,
  the explicit child environment remains isolated, and no SDK `api_key`,
  browser field, prompt context, provider block or runtime fallback is added.
  Existing tool rejection, output bounds, deadlines, cancellation and cleanup
  behavior are retained.
- `test_advice.py` / `test_auth.py`: fake cases cover default and configured
  settings, exact limits, safe rejection, direct construction, key-required
  availability, app wiring and pinned SDK execution/environment propagation.
  Existing default isolation and lifecycle regressions remain in the suite.
- `deploy/.env.api.example` / `deploy/README.md`: empty optional placeholders
  and private key/base/model editing at `/etc/novelai/api.env`, one-time copy
  semantics and idle restart instructions match the implementation.
- Advice, deployment and API specs match this backend-only configuration
  change. The public advice envelope, OpenAPI, dependency pins, database,
  generation flow and frontend are unchanged.

## Release-helper source review

Read, but did not execute or modify:

- `/tmp/nai-advice-config-baseline.py`
- `/tmp/nai-advice-config-stage.py`
- `/tmp/nai-advice-config-activate.py`

No blocking issue found. The scripts stage committed API sources/locked
dependencies and the adjacent pinned CLI without changing active pointers;
verify exact schema and disposable schema4 readiness; gate restart on idle
work; privately back up original configuration and online SQLite; copy only
authorized key/base/model with captured private pipes rather than secret argv;
preserve unrelated configuration, rows, private image bytes/original expiry,
web assets/pointer and AiQQ configuration/process. The configured runner probe
imports/constructs without lifespan, database creation or a model turn. After
modern startup attempt, later failure retains the modern process/pointer and
configuration for forward repair rather than restarting or restoring the DB.
Production execution and its evidence remain the parent's responsibility.

## Verification

Executed from `apps/api`, all with the clean prefix:

```sh
env -i PATH="$PATH" HOME="$HOME" UV_NO_ENV_FILE=1 UV_PYTHON_DOWNLOADS=never uv --no-config
```

- Frozen dependency sync: `sync --frozen --offline --extra test --extra lint`
  passed (24 installed packages checked).
- Tests: `run --frozen --offline --extra test --extra lint python -m pytest -q`
  passed: **748 tests**, two existing Starlette/httpx/AnyIO deprecation
  warnings, 34.16 seconds. All provider/model behavior uses fakes or disposable
  local data.
- Lint: `run --frozen --offline --extra lint ruff check src tests` passed.
- Lock: `lock --check --offline` passed (25 packages resolved).
- OpenAPI: the full suite's exact deterministic snapshot regression passed;
  `apps/api/contracts/openapi.json` has no diff.
- TypeCheck: no backend type checker is configured; not reported as passed.
- `git diff --check` passed.

No frontend/helper/browser automated tests or frontend build were run because
this follow-up changes no frontend source. This reviewer did not read private
env files or production process credentials, issue tokens, deploy, commit,
or call an AI/image/provider endpoint.
