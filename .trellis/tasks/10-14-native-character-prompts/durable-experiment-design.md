# Durable Server-Owned Style Experiments

## Authorization and Change Boundary

On 2026-10-15 the operator additionally requested that failed groups do not
stop the batch, closing the page does not stop execution, and re-entry attaches
to the same run. This supersedes the browser-only scheduler/no-continuation
exclusions in earlier experiment and seven-day retention documents. Continue
the existing authorized task and paired release; no new permission gate.

The behavior belongs in API/SQLite scheduling, not a browser unload workaround.
API implementer owns apps/api models, migrations, orchestration, tests and
OpenAPI; web implementer owns apps/web API/store/components/styles. Parent owns
artifacts, specifications, integration, commits and release. Preserve concurrent
edits. No browser/frontend/helper tests, paid probes or configuration changes.

## Interface (Frozen Shared Contract)

Keep saved-result GET /api/style-experiments list/detail unchanged. Add:

- POST /api/style-experiment-runs, body `{id: UUID, parameters:
  GenerationRequest, ranges: [{tag_index: int, min: str, max: str, step: str}]}`.
  parameters.experiment must be absent/null. Return 202 RunState. Validate all
  settings and the entire compact plan before acceptance; never materialize
  the Cartesian product. Same owner/id/identical validated definition is
  idempotent, including after completion; a different definition is 409
  experiment_run_conflict. Refuse an already-used saved experiment id.
- GET /api/style-experiment-runs/active -> `{run: RunState | null}`. Register
  before the /{id} route. At most one running/stopping run per owner, enforced
  transactionally/with a partial unique index. A second active id returns
  409 experiment_run_active. Ordinary generation remains its existing API.
- GET /api/style-experiment-runs/{id} -> RunState; foreign/missing -> 404.
- POST /api/style-experiment-runs/{id}/stop -> RunState, idempotent. Explicit
  stop prevents new groups; already accepted/claimed current group may finish.

RunState fields: id, status ('running'|'stopping'|'stopped'|'completed'),
total, next_ordinal, processed_count, succeeded_count, failed_count (all exact
decimal strings), current_ordinal (string|null), current_job_id (string|null),
seed (int), sample_count (int), parameters (frozen original GenerationRequest),
ranges (same snake_case range objects), created_at, updated_at (epoch seconds),
error_code (string|null; safe latest diagnostic, not a halt state).

## Compact Plan and Seed

- Reuse the browser's supported prompt grammar: escaped/balanced separators,
  numeric outer groups, unsupported literal emphasis, duplicate occurrences,
  unweighted tags and neutral 1.0 unwrapping. Server parses source; do not trust
  JavaScript UTF-16 offsets as Python character offsets. tag_index is occurrence
  index, not a string search. Reject invalid/duplicate/unadjustable selections.
- Port exact decimal/mixed-radix behavior without binary floats or Decimal
  context rounding: count=floor((max-min)/step)+1, last occurrence varies
  fastest, max only when reached, negative weights supported. Keep existing
  3000-character combined/style bounds, 100-char weight and 1000-digit total
  metadata limits. Selected labels/indexes must satisfy saved metadata bounds.
  Conservatively validate maximum rendered length before starting paid work.
- Freeze prompts, independent characters/coordinates, model/sampler/settings,
  plan and total. Select one random effective seed at accepted run creation if
  seed was blank; persist it once. Use that seed for first and all later groups,
  even if the first group fails. Never re-read draft values or choose another
  seed after failure, reload or service restart.

## Durable Scheduler and Failure Semantics

- Add explicit migration 0003_style_experiments.sql, SCHEMA_VERSION=3. Persist
  compact definition, cursor, counters, stop status, seed and current job id
  in a private owner-scoped table. No PNG in SQLite; retention stays seven days.
- One server lifecycle scheduler, one ordinal in flight per run, using the
  existing bounded single-worker GenerationManager and result reservation
  path. Do not create a second provider executor or bypass admission limits.
  Use a bounded (approximately one second) cadence for rejection-only runs.
  Queue contention waits for capacity; it does not consume/skip a combination.
- A transaction owns claim+queued job creation+current id/cursor update, or an
  equally strong recoverable metadata lookup. Stop and claim serialize, and
  uniqueness prevents duplicate owner/id/ordinal. Persist accepted job identity
  before provider work. Internal runs may persist failed placeholder jobs for
  definite storage/provider admission refusals; public ordinary POST refusal
  still has no seed/history/provider side effects.
- Provider, validation-result, storage and ordinary job failures are recorded
  against that group, counted and followed by the next group. Never retry the
  same ordinal automatically, including outcome_unknown. Final completion may
  contain failures; show success/failure counts. No tight retry loop on refusal.
- On restart GenerationManager first marks old queued/running jobs interrupted.
  Reconcile a run's persisted current job/ordinal, count that group once, and
  continue only with a new ordinal. Never resubmit uncertain paid work. A crash
  between job creation/attachment must find the already saved group before
  advancing; a crash after completion/counter update must not double count.
- Forbid deleting a group's history while its server run is active so recovery
  cannot lose deduplication state. Terminal run history remains deletable.
- Browser close, disconnect, session expiry and logout detach observers only;
  they do not stop the owner-authorized run. API shutdown stops scheduling
  before shutting down GenerationManager; persist remaining work for startup.
  Constructor/OpenAPI remain side-effect free. Production remains one API
  process; no distributed queue/dependency is introduced.

## Browser Ownership and Reattachment

- Replace the browser's paid per-group loop with one run-creation POST and
  read-only polling. Keep exact local preview. Entry/login checks active run
  once and attaches to its frozen definition/progress without modifying draft.
  Handle active-check errors visibly with retry; don't permit a second start
  while active status or an uncertain creation remains unresolved.
- Known client UUID permits read-only GET reconciliation after lost POST
  response; never auto-repeat POST or submit ordinary groups. A transient poll
  failure means disconnected observation, not a stopped server run. Allow
  reconnect and manual Stop; show what actually succeeded/failed.
- Retain normal-generation uncertainty/ownership guards. Attached active run
  locks overlapping normal/start operations locally; session/epoch/abort
  guards prevent stale creation/poll/stop responses changing a later session.
  Logout/dispose revoke local URLs/observers only, with no implicit Stop call.
- Use saved-results lazy comparison for server runs (current image only,
  arrows across groups). Keep viewing independent from draft and run owner;
  expose compare/refresh while running and after completion. Show server
  snapshot source/ranges/sample count after reattachment. No entire-run PNG
  loading or growing live in-memory result archive. Preserve old history view.

## Verification and Release

Meaningful fake-only backend tests: decimal/parser parity and limits; frozen
coordinates/settings; first failure and fixed/random seed consistency; failure
continues; idempotency/concurrent create/owner isolation; stop boundary; close
observer-independent execution; restart at claim/accepted/completion windows,
no repeated ordinal/paid call; queue/storage admission and placeholder groups;
active delete guard; migration v2->v3 preserving auth/jobs, backup/schema probe.
Full frozen offline pytest/Ruff/lock, reviewed OpenAPI and independent combined
check. Web ESLint/TypeScript/source review only; fresh env-free build.

Release requires verified private online v2 backup, no active paid jobs/runs,
stop API, migrate using staged new CLI as service user, verify schema3/integrity,
API-first start/readiness/schema/private image modes then exact web hashes.
After migration retain compatible new API on web fallback; never restore live
DB or switch to schema2-only API. Preserve credentials/env/units/Nginx. Old
temporary images should be downloaded before first restart. No paid smoke test.
