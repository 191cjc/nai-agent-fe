# Backend Submission Refusal Verification

Date: 2026-10-15. Scope: the dedicated missing-executor exception and its
generation POST mapping. No queue, retry, provider, persistence schema or
public request/response model changes were made.

## Contract and Regressions

- `GenerationNotConfigured` is raised only at the initial missing-executor
  guard, before capacity acquisition, seed resolution, history creation or
  enqueue. Generation POST catches only that exception and retains the
  existing `503/provider_unavailable` response.
- A missing executor is tested with a fake configured provider but no started
  worker. Spies confirm no capacity acquisition, random seed, history create
  or worker call; the request seed stays null and no provider call occurs.
  The existing disabled-provider API test verifies the public 503 pair and
  absence of parameter history.
- A generic RuntimeError from history creation, both before and after its
  real SQLite commit, returns generic HTTP 500. Already-created history
  remains queued and inspectable; no executor/provider call occurs.
- A fake executor submission records an enqueued work item and then raises
  RuntimeError. The response is generic HTTP 500, not a configuration refusal;
  exactly one work item and its original queued history remain, without any
  provider invocation or automatic retry.
- Existing accepted-job provider exception handling is unchanged. The full
  suite still covers terminal failures, cache removal and secret-safe output.

## Checks

Every child process received only normal PATH/HOME plus
`UV_NO_ENV_FILE=1` and `UV_PYTHON_DOWNLOADS=never`. UV configuration discovery
was disabled with `--no-config`; run commands explicitly used `--no-env-file`.
No environment files or provider credentials were read or inherited.

From `apps/api`, all commands exited 0:

```sh
uv --no-config sync --frozen --offline --extra test --extra lint
uv --no-config run --no-env-file --frozen --offline --extra test --extra lint python -m pytest -q
uv --no-config run --no-env-file --frozen --offline --extra lint ruff check src tests
uv --no-config lock --check --offline
```

- Full backend suite: **215 passed in 9.97 seconds**, with two pre-existing
  dependency deprecation warnings from Starlette/httpx and AnyIO.
- Ruff: all checks passed. Frozen sync: 24 installed packages checked.
  Offline lock check: 25 packages resolved.
- `git diff --check`: passed. No configured Python type checker is claimed.
- The OpenAPI snapshot regression passed without changing its metadata or
  checked-in JSON. SHA-256 remains
  `d622c2baff6da8fb550516286f600570670fb79c5db5e66d73449480b4b6dda6`.

No frontend/helper/browser automated tests, live network/provider calls,
production/configuration/credential access, commit or deployment was performed
by this backend implementer.

## Stable Source SHA-256

| File | SHA-256 |
| --- | --- |
| `apps/api/src/novelai_api/generations.py` | `8c61864dd831ffc338b07048c3a16351d2df1b38aa536ad3ab85b6fe66a6941e` |
| `apps/api/src/novelai_api/app.py` | `befb992628ea0c0474fa5bf3689fc3df63f7723681c493ce6c07c55ecb11bba6` |
| `apps/api/tests/test_generations.py` | `2bfc5d9cf1d1039e351c361f47016d6c5d038ed4ac24a245e9a3e3831f3f6cf1` |

Independent combined API/web review remains for the parent. The narrow
frontend classification must not be deployed against the old broad API catch.
Preparing this fix does not configure image generation or prove paid output;
production switching/restart and credential setup remain a separate gate.
