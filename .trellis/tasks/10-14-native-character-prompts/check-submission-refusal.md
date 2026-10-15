# Independent Check: Definite Submission Refusal

Date: 2026-10-15. Scope: the current submission-refusal follow-up diff,
task PRD/design/implementation plan, all check.jsonl context, frontend and
backend spec indexes, and owning browser/API source paths.

## Frontend Review

The only browser source change is GenerationStore.submitParameters' POST
catch in apps/web/src/store.ts. No mechanical frontend fix was needed.

- Only an ApiFailure with status 503 and code provider_unavailable gets the
  not-configured message and submitUncertain=false. Mismatched pairs such as
  503/request_error or 502/provider_unavailable, all other 5xx, network and
  non-ApiFailure failures, and successful-response JSON parsing failures
  retain the conservative unknown-outcome lock. Ordinary definite 4xx keeps
  errorText behavior.
- The catch releases busy/operation ownership, returns without a successor
  POST, and does not call accepted or terminal history notifications. For an
  experiment it first marks the current run failed, preserves existing
  comparison rows, then clears execution. Stop during a pending POST cannot
  cause the failure to advance the sequence. No automatic paid retry was
  introduced.
- Classification remains inside the sole generation POST path. Accepted
  jobs' provider_unavailable terminal errors still flow through refresh and
  errorText, retaining their existing separate meaning, result/history state
  and experiment halt behavior.
- Epoch and operation-token checks reject stale catch/acceptance results.
  Logout/clear while a POST is pending retains uncertainty; failed logout
  does not resume an experiment. Session expiry resets protected state, and
  stale responses cannot restore it. Acknowledgement only clears the lock
  and message; it never submits or restarts a run. The existing history and
  manual-recheck paths remain unchanged.
- Structured prompts, native character boundaries, sampler draft/manual
  settings, experiment snapshots/seeds and archived image ownership are
  unchanged. Their owning paths were reviewed where they call or render
  this submission flow; earlier verified helpers were not re-tested.

## Finding Fixed and Independently Rechecked

The first review identified that app.py caught every RuntimeError from
manager.submit and mapped them to 503/provider_unavailable. History creation
preceded executor submission, and Python 3.12's executor queues work before
starting a worker thread. A later RuntimeError therefore could not establish
pre-acceptance refusal. This cross-layer issue was reported to the main
session rather than silently widened beyond the initial review ownership.

The backend follow-up now defines GenerationNotConfigured and raises it only
at the initial missing-executor guard, before capacity acquisition, seed
resolution, history creation or enqueue. The route catches only this type.
Ordinary history/executor RuntimeErrors propagate as generic 500 failures,
which the browser keeps outcome-uncertain. No retry, queue algorithm, provider
error mapping, dependency, schema or request/response model was changed.

The four added regression cases cover missing executor with no submission
side effects, history failure before persistence, history failure after
persistence, and fake executor failure after queue insertion. The latter
cases retain any created history and never claim configuration refusal; fake
providers receive no calls. Existing disabled-provider API coverage still
checks the exact public 503 pair and absence of history. The full suite also
retains accepted-job terminal failure and secret-safe API checks.

Current PRD, implementation plan, research and frontend/backend contracts
agree with the corrected boundary and require API-first matched rollout.
The former web-only publication plan is explicitly superseded. Do not publish
this browser classification against the old broad RuntimeError handler.
The prepared enablement plan and both updated contracts also preserve the
corrected API after any web rollback: open tabs can continue running the new
classification. Only a failure before corrected-web activation permits
restoring the old API/environment; after activation, web/environment rollback
must retain the dedicated refusal fix and can leave generation unavailable.
The combined source/static/offline quality gate now passes; no outstanding
source findings remain and this reviewer made no source changes.

## Verification Actually Run

- `python3 .trellis/scripts/get_context.py --mode packages`: completed;
  single repository, backend/frontend layers. Both layer indexes and their
  applicable active contracts were read. The frontend quality template adds
  no executable project-specific checks; workspace-contract governs these
  checks. Package discovery and current context/spec diffs were reread for
  the combined final-scope check.
- `npm run lint` in apps/web: pass; executes `eslint . && tsc --noEmit`.
  The process received an allowlisted environment with normal
  HOME=/home/ubuntu, explicit Node v24.19.0 PATH, CI/LANG, HTTPS npm registry,
  and two distinct empty temporary user/global npmrc files. No inherited
  provider configuration was passed. An initial system-only PATH could not
  locate npm; adding the known Node installation allowed the checks to run.
  The browser source hash is unchanged on the combined recheck, so this
  successful check remains valid without repeating it.
- Independent backend check: every subprocess received only explicit normal
  PATH/HOME, UV_NO_ENV_FILE=1 and UV_PYTHON_DOWNLOADS=never. Configuration
  discovery and env-file loading were disabled; commands ran offline from
  apps/api. All four commands below exited 0:

  ```sh
  uv --no-config sync --frozen --offline --extra test --extra lint
  uv --no-config run --no-env-file --frozen --offline --extra test --extra lint python -m pytest -q
  uv --no-config run --no-env-file --frozen --offline --extra lint ruff check src tests
  uv --no-config lock --check --offline
  ```

  Full suite: **215 passed in 9.03 seconds**, with the same two dependency
  deprecation warnings (Starlette/httpx and AnyIO). Ruff passed over src and
  tests; frozen sync checked 24 packages and lock check resolved 25 packages.
  No Python type checker is configured or claimed.
- API metadata/model definitions and the deterministic OpenAPI regression
  were reviewed. The snapshot is unchanged and its full-suite comparison
  passes; unhandled generic server failures do not become typed configuration
  refusals. No public schema or snapshot regeneration was needed.
- `git diff --check`: pass, including this verification record.
- Frontend/helper tests and browser automation: not run, as explicitly
  prohibited. No generation/advice/provider calls, credential/environment
  reads or production changes were made by this reviewer.
- Fresh isolated build, production hashes/health, provider configuration and
  real output verification were not performed by this reviewer. Readiness
  only checks the database; it is not proof of image generation availability.

## Stable Reviewed Source SHA-256

| File | SHA-256 |
| --- | --- |
| apps/web/src/store.ts | `58382748bc208938d1d2406291d5914def48ff9ac3e1a7383ee03deaf498a0d9` |
| apps/api/src/novelai_api/app.py | `befb992628ea0c0474fa5bf3689fc3df63f7723681c493ce6c07c55ecb11bba6` |
| apps/api/src/novelai_api/generations.py | `8c61864dd831ffc338b07048c3a16351d2df1b38aa536ad3ab85b6fe66a6941e` |
| apps/api/tests/test_generations.py | `2bfc5d9cf1d1039e351c361f47016d6c5d038ed4ac24a245e9a3e3831f3f6cf1` |
| apps/api/contracts/openapi.json | `d622c2baff6da8fb550516286f600570670fb79c5db5e66d73449480b4b6dda6` |

All assigned source and verification-record ownership is returned to the
main session. Matched release preparation may proceed. Production
activation/configuration/restart authorization and real-provider acceptance
remain separate pending gates; offline success does not configure a provider.
