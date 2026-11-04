# Durable Style Experiment Scheduler

## Scope / Trigger

Use for batch creation, progress, Stop, API lifecycle, generation admission or
schema changes affecting server-owned style experiments. The operator requires
failure continuation and background execution independent of browser lifetime.
This replaces earlier browser-only/no-continuation contracts.
Fixed-style dataset runs are a second run kind sharing this lifecycle; see
[Dataset Runs and Export](./dataset-run-contract.md).

Whole-line per-tag comments and raw/effective projections follow
[Individual Hidden Tags](./prompt-comments-contract.md). Syntax is opt-in per frozen request;
absent/false preserves the legacy contracts below.

## Signatures

- POST /api/style-experiment-runs: `{id: UUID, parameters: GenerationRequest,
  ranges: [{tag_index, min, max, step}]}` -> 202 RunState.
- GET /api/style-experiment-runs/active -> `{run: RunState|null}`.
- GET /api/style-experiment-runs/{id} -> RunState.
- POST /api/style-experiment-runs/{id}/stop -> RunState (idempotent).
- RunState: id, status, total, next_ordinal, processed_count, succeeded_count,
  failed_count, current_ordinal, current_job_id, seed, sample_count, parameters,
  ranges, created_at, updated_at, error_code. Counts/ordinals use exact decimal
  strings; nullable current fields; safe latest error diagnostic.
- Migration 0003_style_experiments.sql introduced the run table at schema3.
  Current SCHEMA_VERSION=4 also includes the private prompt snapshot library;
  see [Prompt Sections](./prompt-sections-contract.md). Images remain separate
  private files; see [Image Retention](./image-retention-contract.md).

## Contracts

- One running/stopping run per owner, transaction/index enforced. Same
  owner/id/definition returns the existing state; changed definition or reused
  metadata-only id conflicts. Parameters exclude nested experiment metadata.
  Authentication, mutation Origin checks, no-store and owner 404 apply.
- Freeze the entire request/coordinates and compact source-order range plan.
  Parse occurrence indexes server-side; never trust browser UTF-16 spans.
  Match escaped/balanced prompt syntax and exact scaled-integer decimal math.
  Last source occurrence varies fastest; include only grid points <=max.
  Neutral 1.0 removes the outer numeric wrapper; preserve remaining source.
  New definitions use internal plan_version2: exact zero removes the selected
  parsed occurrence and its neighboring separators, while ExperimentWeight
  retains the original tag index/label and `0.0`. No string-wide removal of
  duplicate labels. Source-span removal follows the frontend experiment
  contract, with Python offsets parsed independently from browser UTF-16.
  Validate all metadata/prompt limits before acceptance, without allocating
  combinations or imposing a hidden product truncation.
- Keep persisted version1 plans on their original numeric-zero rendering and
  validation after restart. Carry the definition version internally; it is
  not a public RunState/OpenAPI field or schema migration. Same-owner/id with
  matching normalized parameters/ranges still returns its legacy definition;
  version alone does not create a conflict. Never rewrite or replay old groups.
- New plans reject reachable all-zero style combinations when shared prompt
  is blank before any run is accepted. Use exact grid divisibility, not product
  enumeration or a check of only the first group. All removed style is empty;
  with shared content its base has no extra comma. Zero-only dimensions shrink
  the conservative rendered bound; preserve raw/trimmed field limits.
- Persist one effective seed at run creation (random once if blank) and use
  it even when the first or a later group fails. Never read later draft edits.
- Freeze auto_character_position alongside coordinates and other settings.
  Old saved definitions omit it and retain the new request model's manual
  false default. Canonical same-id comparison may supply only that missing
  false mode for compatibility; do not rewrite raw definitions, drop unknown
  keys or equate a changed true mode. Preserve plan_version1/2 semantics.
- Freeze optional prompt_sections metadata with all hidden text/state and source
  axes. Absent None is excluded from model_dump/model_dump_json so old same-ID
  definitions require no new normalization. Effective fields must match the
  metadata; style-only group overrides preserve it. Changed hidden metadata
  still conflicts even if effective prompts match. See prompt-sections-contract.md.
- Single lifecycle scheduler on GenerationManager's per-lane executors: lane
  `novelai` (NovelAI provider, ordinary generation, style and non-GPT dataset
  runs) and lane `gpt` (GPT image character groups), each one worker with its
  own 3-slot bounded admission, so one provider never waits behind the other.
  A run's lane is frozen at create (`style_experiment_runs.lane`, schema 9).
- Run queue (schema 9): an owner may hold up to 10 unfinished runs
  (`MAX_ACTIVE_RUNS`, else 409 `experiment_run_queue_full`). Within one
  owner's lane only the oldest unfinished run (ORDER BY created_at, rowid)
  claims groups; later runs wait with no claim, history or paid call.
  `queue_position` (0 executing, N waiting behind N) is reported by run reads
  and `GET /api/style-experiment-runs/queue` (oldest first, with names).
  Stopping a waiting run settles it immediately as stopped. `GET .../active`
  remains and returns the oldest unfinished run. At most one group per run in flight. Queue
  contention waits without consuming a group. Rotate the starting owner across
  bounded scheduler ticks so earlier continuously active owners cannot starve
  later runs. Definite admission failures may
  create internal failed placeholders; ordinary POST refusal stays side-effect
  free. Refusal-only progression uses a bounded cadence, approximately 1s.
- Persist current group identity/cursor before provider work, with transactional
  claim+job creation or equally strong recoverable uniqueness. Stop serializes
  with claim; current accepted group may finish, later groups cannot start.
- Count each terminal group once, advance after success/failure, never auto
  retry a group (including outcome_unknown). On restart reconcile interrupted
  jobs and proceed to a new ordinal. While a worker is still live it owns its
  outcome; if terminal persistence failed and its admission has ended, reconcile
  the orphan current as outcome_unknown once the DB returns, never resubmit it. Browser close, logout and disconnect only
  detach observers. Shut scheduler down before executor shutdown.
- Block deletion of active-run groups until the durable run settles. Counters
  are durable; do not reconstruct progress from deletable history counts.
- Construction/schema probes create neither DB nor state. Explicit migration
  runs as service user after verified backup and stopped old API. After v3
  migration never restore live DB or start the old schema2-only API; web fallback
  retains new compatible API and private images.

## Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid plan/settings/nested metadata | 422 before paid work |
| New all-zero-reachable style and blank shared | 422 before run creation |
| New selected zero weight | Omitted from provider style; retained in metadata |
| Stored v1 zero group after restart | Original numeric-zero semantics |
| Existing same owner/id/definition | Return existing run; no duplicate work |
| Same id with changed definition | 409 experiment_run_conflict |
| Owner already holds 10 unfinished runs | 409 experiment_run_queue_full |
| Earlier unfinished run in the same owner lane | 202; new run waits (queue_position > 0) |
| Foreign/missing run | 404 |
| Group provider/storage/outcome failure | Failed history + counter, continue next ordinal |
| Queue temporarily full | Wait without consuming ordinal |
| Explicit Stop | Persist stopping/stopped; no new claim |
| Browser closed/poll disconnected | Server keeps running; later GET reconnects |
| Service interrupted during paid group | Never resubmit that ordinal; reconcile once |

## Good / Base / Bad Cases

- Good: group 2 fails, groups 3..9 continue with the same seed while the browser
  is closed. Re-entry reads server progress and compares retained images.
- Base: one-value run completes once; repeated create/Stop calls are harmless.
- Bad: reconnect POSTs the same combination, a failed first group picks another
  seed, or Stop races a nontransactional next-group insertion.

## Tests Required

Disposable SQLite/fake providers only: exact parser/decimal golden cases and
limits, first-failure seed reuse, frozen coordinates/settings, failure
continuation, idempotency/concurrent active creation, owner isolation/Origin,
Stop/claim race, admission/capacity release, failed placeholders, restart at
claim/paid/completion windows with no duplicate calls, active deletion guard,
v2->v3 upgrade preserving auth/jobs and private backup. Full backend quality
gate and OpenAPI review; frontend static/source checks only, no paid probes.
Zero-omission regressions must assert exact prompts/metadata at the fake
provider and saved history, separator/Unicode/duplicate/nested syntax cases,
empty and near-limit bounds, signed/precise zero grids and legacy v1 restart
and idempotency. Do not regenerate OpenAPI for this internal-only change.

## Wrong vs Correct

- Wrong: a browser unload handler keeps a loop alive, or a lost response causes
  an automatic paid retry.
- Correct: the server persists run/cursor and the browser only observes GET
  state; failures advance to a new ordinal, never repeat the uncertain one.
