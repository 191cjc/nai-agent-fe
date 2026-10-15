# Research: Durable server style-experiment scheduler

- Query: Continue after each failed group until all combinations or explicit Stop; browser closure/logout must not stop work, authenticated reentry reconnects; restart never duplicates a paid ordinal.
- Scope: internal source inspection; includes the concurrent image-retention implementation as observed on 2026-10-15. Read-only outside this research file, no paid calls/browser tests.
- Date: 2026-10-15

## Findings

### Files and current code patterns

| File | Relevant pattern |
| --- | --- |
| `apps/web/src/prompt-weights.ts:24-66` | ASCII decimal grammar, exact bigint scaled arithmetic and canonical decimal formatting. |
| `apps/web/src/prompt-weights.ts:74-156` | Escaped/balanced-scope tokenizer; occurrence indices and original spans; unknown/unsafe syntax cannot be adjusted. |
| `apps/web/src/prompt-weights.ts:168-184` | Exact numeric wrapper replacement and neutral-weight unwrapping. |
| `apps/web/src/style-experiment.ts:38-87` | Validate/normalize dimensions, sort by source order, compute Cartesian total and length preflight without materializing requests. |
| `apps/web/src/style-experiment.ts:91-106` | Decode one mixed-radix ordinal; last source dimension varies fastest; replace spans right-to-left. |
| `apps/web/src/store.ts:414-515` | Current browser Start/Stop and each-group reconstruction; all settings/characters frozen. |
| `apps/web/src/store.ts:643-667` | Current terminal settlement stops on job/image failure, then browser timer creates successor. This is the behavior being replaced. |
| `apps/api/src/novelai_api/generations.py:51-102` | New saved metadata: `experiment: {id,ordinal,total,weights}`, canonical positive ordinal/total strings <=1000 digits, weights <=100 characters. |
| `apps/api/src/novelai_api/generations.py:228-257` | `JobStore.create` writes request/effective seed, rejects duplicate/inconsistent metadata in a write transaction. |
| `apps/api/src/novelai_api/generations.py:259-284` | Startup marks all queued/running jobs failed/outcome_unknown; running/finish are status-guarded writes. |
| `apps/api/src/novelai_api/generations.py:489-610` | New idempotent admission release; disk reservation; global one-worker executor, three accepted slots; startup/stop. |
| `apps/api/src/novelai_api/app.py:327-364` | New `/api/style-experiments` list/detail are saved-group metadata/image viewing, not scheduler state. |
| `apps/web/src/saved-results.ts:13-217` | New independent lazy read-only archive store owns current Blob, selection/session epochs and cancellation. |
| `apps/api/src/novelai_api/db.py:39-55,59-104` | Fresh short-lived connections, `BEGIN IMMEDIATE` writes, explicit migrations and schema-version readiness. |
| `apps/api/src/novelai_api/migrations/0002_generations.sql` | Existing generation/history rows; no scheduler state. |

Line anchors above describe the working tree during parallel implementation and may move before check. Existing retention research is `research/image-retention-contract.md`; this follow-up supersedes its browser-only-scheduler recommendation.

### Shared API shape, aligned with parent direction

Keep scheduling separate from saved-group/image browsing:

```text
POST /api/style-experiment-runs
  {id: UUID, parameters: GenerationRequest, ranges: ExperimentRange[]}
  -> 202 RunState

GET /api/style-experiment-runs/active
  -> 200 {run: RunState|null}

GET /api/style-experiment-runs/{id}
  -> 200 RunState, owner-scoped 404 when absent/foreign

POST /api/style-experiment-runs/{id}/stop
  -> 200 RunState (idempotent; exact same terminal state if already ended)

ExperimentRange = {tag_index: number, min: string, max: string, step: string}

RunState = {
  id: UUID,
  status: 'running'|'stopping'|'stopped'|'completed',
  total: string,
  next_ordinal: string,
  processed_count: string,
  succeeded_count: string,
  failed_count: string,
  seed: number|null,
  current_job_id: string|null,
  sample_count: number,
  parameters: GenerationRequest,
  ranges: ExperimentRange[],
  created_at: number,
  updated_at: number
}
```

- Define `next_ordinal` as next **unclaimed** one-based ordinal, initially `"1"`; after all claims it is `total+1` (allow 1001 digits if a 1000-digit total ends in all nines). `processed_count` means settled success+failure, not successful images; completed run may have failures. Queue/current job status remains in the ordinary job endpoint. Add `last_error_code: string|null` only if the UI needs a latest failure summary; individual failed groups already have error codes.
- `parameters.experiment` must be absent/null on create. Server supplies immutable saved-group metadata; original run `parameters` remains the original source/frozen settings with requested seed, while `seed` is the latched effective request seed. Never mutate the draft during reconnect. Nested character x/y and sample count remain frozen.
- Keep existing saved endpoints `/api/style-experiments` and `/api/style-experiments/{id}` unchanged. Every server-produced group uses the same run UUID in `parameters.experiment`; existing history/viewer therefore works for success, failure and expiration. A just-created run with no group may not appear there yet; RunState is still discoverable through `/active`.
- Idempotency uses the client UUID and owner: identical normalized definition returns the existing run without creating/queuing anything; differing definition under the same ID returns 409. Repeated creation must not reset a stopped/completed run. Canonical comparison must use original parameters/ranges, not the latched runtime seed or counters.
- One owner may have only one `running`/`stopping` run. Enforce in the DB, not a browser flag. Return 409 for another active run with a different ID. Register literal `/active` before `/{id}`. Create/Stop retain same-origin mutation checks; all endpoints require the existing session and safe ApiError responses.
- Keep ordinary `/api/generations` definite-refusal behavior unchanged. New internal failed-group placeholders do not make ordinary missing-provider/storage-refused POSTs create history. Reject public legacy group POSTs trying to append to a scheduler-owned run ID; otherwise an old tab could conflict with or inject groups into the durable sequence.

### Compact persisted plan and exact render parity

The smallest public plan is the frozen `parameters.style_prompt` plus normalized range triples selected by `tag_index`. Do not submit all Cartesian requests or client numeric span offsets. JavaScript source positions count UTF-16 units while Python string indices count code points; a range after an emoji would otherwise target the wrong text.

Recommended stored definition:

```json
{
  "plan_version": 1,
  "parameters": {"style_prompt": "artist:a, artist:b", "...": "other frozen settings"},
  "ranges": [
    {"tag_index": 0, "min": "0.8", "max": "1.2", "step": "0.2"}
  ]
}
```

The server parses/compiles this O(source length + selected dimensions) definition and stores the normalized definition (or a versioned compiled plan with server-local spans). Cache compilation in memory for active runs, reconstruct it on restart. Persist only scalar cursor/state; derive one request from its ordinal when needed.

Port the actual source tokenizer/setter and arithmetic, not `source.split(',')`, a regex of artist names or naive `(tag:weight)` replacement:

1. Token boundaries occur at comma/CR/LF only outside escaped and balanced numeric/bracket scopes. Trailing escaped whitespace and unsafe/incomplete syntax stay original; duplicate labels remain separate occurrences. The initial numeric prefix has boundary restrictions (`prompt-weights.ts:27-29`). Preserve all unselected characters.
2. Decimal parser accepts ordinary signed decimal input (including `+.5` and leading zeros), rejects exponent/nonfinite values, normalizes integer/fraction zeros, keeps at least one fractional digit (`1 -> 1.0`, `-0 -> 0.0`). Canonical frontend dimensions already provide normalized strings. Use integer units + scale; Python `Decimal` with its default precision 28 is insufficient for existing allowed 100-character weights.
3. Count axis values using an exact common scale for min/max/step: `floor((max-min)/step)+1`; require step>0 and min<=max. Emit at scale `max(minPlaces,stepPlaces)`. Include max only when on the grid.
4. Sort axes by source occurrence. Decode zero-based `ordinal-1` from last axis backward using modulo/division; rightmost axis varies fastest. Start from the immutable source for each combination, replace selected spans from right to left.
5. For an existing numeric wrapper and nonneutral weight, replace only the numeric prefix. For exact neutral `1.0`, remove its outer weight + `::` and final `::`, preserving body whitespace, escapes and nested content. For a plain neutral tag, leave its original source unchanged. For a plain nonneutral tag, wrap exactly its trimmed occurrence source. Preserve saved weight label `1.0` even when prompt serialization is unwrapped.
6. Port conservative maximum style-length preflight, including the special single neutral grid point that shrinks an existing wrapper (`style-experiment.ts:74-76`). Off-grid max just above 1 can still produce only neutral. Validate combined style/shared maximum before accepting the run. Validate each derived request as a defense, without allocating every combination.
7. Respect current metadata limits: total<=1000 digits, selected dimensions<=1500, tag index<=2999, each rendered weight<=100 characters and aggregate selected labels<=3000. A new limit is a visible preflight rejection, never silent truncation. The server is authoritative; browser helper remains a preview.

Python/JS pitfalls to account for: Python regex `\d` includes Unicode digits while JS here accepts ASCII; use `[0-9]`. JS `\s`/trim includes U+FEFF but differs from Python `str.strip` around U+0085/control characters. UTF-16 length is also different from code-point length for astral characters; a tiny `utf16_length` helper can preserve browser's existing 3000-character/label budget when required. Keep the actual field-validation limits explicit rather than silently treating language builtins as identical.

### Migration 3 and transactional state

Add a dedicated `style_experiment_runs` table through `0003_style_experiment_runs.sql`, `SCHEMA_VERSION=3`, explicit migration ordering and readiness table checks. No image bytes enter SQLite. A suitable minimum row is:

```text
user_id, id                         composite primary key (owner + UUID)
definition_json                    versioned normalized original definition
status                             checked running/stopping/stopped/completed
total TEXT                         canonical positive decimal
next_ordinal TEXT                  canonical positive decimal, may equal total+1
processed_count INTEGER DEFAULT 0
succeeded_count INTEGER DEFAULT 0
failed_count INTEGER DEFAULT 0
effective_seed INTEGER NULL
current_job_id TEXT NULL
created_at INTEGER, updated_at INTEGER
```

Use a unique partial owner index where status is running/stopping. Counters may use SQLite INTEGER internally because they count actual accepted/settled rows, but serialize as decimal strings and do not cast total/cursor to SQL integers. If a true arbitrary-count guarantee is required, persist counters as canonical TEXT too and increment with Python ints inside the write transaction. Do not derive progress from COUNT of remaining history: users may delete old groups.

`current_job_id` should either use `REFERENCES generation_jobs(id) ON DELETE RESTRICT` while current, or deletion must check references in the same transaction. A terminal current group cannot disappear before it is accounted. Do not hard-restrict all historical jobs forever; once current is cleared, normal individual deletion should work.

Optional strong uniqueness: add nullable scheduler run ID/ordinal columns with a unique `(user_id,scheduler_run_id,scheduler_ordinal)` index to generation_jobs. This supplements, rather than replaces, the run cursor. Existing records get nulls; retain their saved metadata. A separate scheduler-step ledger is another option but is not necessary if every create/settle path reliably uses the current pointer/cursor in one immediate transaction.

Critical transactions:

1. **Create** validates and normalizes the entire compact definition first. In one write transaction, check idempotency, check one active owner, insert run. Pick a seed once either here or in first claim. Picking at create is simplest and still makes the first generated request and every failed/refused placeholder share the same seed. If keeping `seed:null` until first claim, seed assignment and first job insertion must be in that same claim transaction; never wait for image success/GET to latch it.
2. **Claim** in `BEGIN IMMEDIATE`: require running + null current, ensure next<=total, derive one request, use the persisted seed (assign once if absent), insert a queued job with exact experiment metadata, write current job ID and increment next_ordinal. Commit before any provider side effect. Rechecking this state can never claim the old ordinal again. Do not merely call current manager.submit then save its returned ID: a crash between those commits would lose the accepted pointer and risk a duplicate.
3. **Settle** once for the matching current ID: after terminal job, increment exactly one success/failure count, clear current, choose stopped if Stop requested, otherwise completed when cursor>total, otherwise running. Prefer job terminal transition + run settlement in the same transaction. If settlement remains in scheduler polling, forbid current deletion and retain idempotent current-ID checks; a crash between terminal write/settlement can safely settle once after restart.
4. **Stop** in the same DB locking discipline: running with current -> stopping; running without current -> stopped; repeat terminal requests leave the row unchanged. An ordinal claimed before Stop may settle; no claim can commit after Stop returns. Stop never aborts/retries an accepted paid request.

SQL connection transactions must stay short: no provider generation, image I/O, sleeping, semaphore waiting or executor shutdown while holding BEGIN IMMEDIATE. Extract shared insert/finish SQL helpers rather than nesting existing `JobStore.create`/`finish`, which open separate immediate transactions themselves.

### Dispatcher, failure continuation and definite refusals

- Add one small scheduler/coordinator thread with a stop event; it can poll/dispatch at a one-second minimum interval and use the existing single-worker GenerationManager executor for all actual provider calls. Never add another provider executor: that would bypass the one-at-a-time provider contract. Fairly visit active owners; do not permanently starve a later owner's run.
- Every *claimed* ordinal gets a visible saved row. Provider failure, invalid result, outcome_unknown, disk result write error, or enqueue failure settles that group failed, records a safe error code and continues to the next ordinal on a later tick. Fetching/displaying PNGs is no longer part of server progress: a browser image GET failure cannot stop the run.
- Provider-not-configured or disk-admission refusal cannot use public `submit` unchanged: it currently rejects before persistence. New private dispatch can claim its one job, record `provider_unavailable` / `result_storage_unavailable` as a **failed placeholder** without calling provider, then settle and advance. This is one distinct group attempt, not a retry. Pace all immediate refusal paths at >=1 second; do not burn through an enormous product in a tight loop.
- Global queue capacity is preferably checked before claim; waiting for a free slot then claiming is scheduling, not a paid retry. Otherwise an unrelated long ordinary request can turn many combinations into artificial queue_full failures. If product direction treats queue_full as a failed attempt too, define that explicitly and retain one-second pacing. Parent owns that choice.
- Reuse ResultStore.reserve/release and the idempotent `_Admission` object (`generations.py:489-579`). Private enqueue must handle reserved-slot release on any claim/enqueue error, cancellation and shutdown. Do not reserve an entire Cartesian run or hold 32 MiB per future combination. Existing disk budget still refuses new calls without evicting seven-day images.
- For storage/provider definite refusal, seed comes from the frozen run and is saved with the failed group. A first failed group must not leave later groups random or blocked waiting for a successful image.
- Infrastructure DB outages are different from a settled group error: while persistence cannot prove a claim/finish, do not call provider or advance blindly. Retry state reconciliation/readiness later, keeping the same committed pointer. This is not resending an uncertain paid request.

### Startup/shutdown and no duplicate paid calls

| Crash/stop point | Recovery |
| --- | --- |
| Before run/claim transaction commits | Nothing accepted for that ordinal; later claim can create it. |
| After claim commit, before enqueue/provider | Saved queued/current exists; mark interrupted failed and settle once; do not resubmit that ordinal. |
| During paid call or after paid call before terminal persistence | Mark current job failed/outcome_unknown, count it once, move to next distinct ordinal; never replay it. |
| After durable PNG put before succeeded DB write | Conservatively fail interrupted job; image routes require succeeded, so orphan result cleanup must remain safe. Do not infer paid resubmission permission from missing success state. |
| After terminal job write before run settlement | Startup sees terminal current and settles exactly once using current-ID compare. |
| After Stop persisted while current accepted | Startup settles interruption/terminal group then stopped, with no next claim. |
| After run settlement/current cleared | Persisted next ordinal remains authoritative; no backwards scan/restart from last successful image. |

- Start order: explicit migration/readiness -> reconcile old queued/running jobs -> initialize disk store -> reconcile run current pointers/terminal counts -> start provider executor -> start scheduler. Constructors/schema-only OpenAPI calls must not start threads, create state or contact providers.
- Stop order: signal/join scheduler so no successor can be claimed/enqueued -> wait/cancel GenerationManager work (existing cancellation release retained) -> stop disk maintenance. Graceful running jobs may finish; queued canceled jobs remain durable and are reconciled on restart. Shutdown must not rewrite running runs as user-stopped, otherwise service restarts silently stop authorized work.
- The one-worker host model (`deploy/novelai-api.service`) is assumed. Persisted claims/status guards defend ordinary races, but do not claim support for two concurrent scheduler processes without a process/DB lease and ownership protocol. Existing bulk mark_interrupted would otherwise interfere with a live second process.
- Migration 3 blocks downgrade to schema-2 API through current readiness/version logic. Private online backup and coordinated API-first rollout are required; database restore to old schema would lose new writes/run state and must never automatically resume restored paid runs. A provider-free backup drill must not accidentally start the durable scheduler against copied active definitions.

### Browser changes and reconnect

- Keep existing local helper for preview/validation and send one create body. Remove browser `advanceExperiment`, successor timers and per-group submit path from the live experiment workflow. Treat server as the only paid experiment owner.
- Separate generation-draft restore from active-run discovery. On authenticated entry, GET `/style-experiment-runs/active` with its own auth/session epoch; attach polling to that run without replacing the draft. Intervening draft edits should skip prompt auto-restore, not suppress reconnection to an already running server job.
- Browser close, clear view, logout start, failed logout, 401 and dispose cancel polls/Blob requests and release URLs only. They must not call server Stop. Stop is an explicit authenticated button whose pending/error state remains honest; on uncertain Stop response, GET state rather than assume stopped or resume paid work.
- Keep the known client UUID through uncertain create; reconnect via GET that ID or `/active` and never create a new ID automatically. Same-ID create is safely idempotent, but ordinary user actions should still recheck before retrying an uncertain write.
- Poll state independently of image loading. Existing `SavedResultsStore` can supply the paginated lazy comparison for current and old runs; preserve selection while new groups arrive. Avoid re-fetching an unchanged selected Blob every state tick or jumping to latest group. RunState progress does not depend on whether the browser has loaded all results.
- Keep ordinary submit/new-experiment controls locked while an attached run is running/stopping; reconnect must restore those guards before permitting paid actions. Server must guard conflicting active starts regardless of tab. If blocking ordinary same-owner jobs during active experiments is desired to preserve the old noninterleaving rule, enforce it in the public generation route with an internal scheduler bypass, not only the current page.
- A completed run with failures is labeled completed with failed/succeeded counts. Failed/expired groups remain arrow-navigable placeholders. Clear comparison clears local view, not scheduler state, historical rows or retained images.

### Necessary offline tests and spec updates

- Backend golden parsing/render vectors: plain/existing numeric tags; exact neutral and neutral-only off-grid maximum; duplicate labels; nested numeric/bracket scopes; escaped commas/colons/whitespace; malformed syntax; negative/zero/high-precision values; crossing zero; emoji/CJK before selected tag; exact Cartesian order and huge ordinals without request allocation. Assert unrelated source bytes preserved.
- Fake-provider progression: fail first/middle/all groups, continue through all distinct ordinals; same seed after first failure/refusal and across restart; each provider call once at most; first fixed seed preserved; snapshots include sample count and character x/y.
- Barriers around claim/enqueue/provider/finish/Stop and SQLite transactions: duplicate Start same/different definition, competing active Start, Stop before claim/during call/between groups/after completed, restart at each durable phase, counters never double-settle or regress after history deletion, no successor accepted after Stop returns.
- Provider missing/storage refusal yields failed placeholder with zero provider calls and no duplicate ordinal; queue contention behavior follows chosen contract; one-second pacing and shared single-worker execution; cancellation/admission reservations released exactly once.
- Migration v1/v2 -> v3 idempotently preserves tokens/sessions/history and restrictive file modes; backup/restore includes run definition/state but no PNG bytes; provider-free recovery cannot auto-spend. Update old exact `user_version == 2` assertions (`tests/test_auth.py:253`) and readiness/newer-schema failure cases.
- API owner/origin/isolation, UUID/decimal/range/length validation, deterministic OpenAPI/no-constructor-side-effects, existing ordinary refusal behavior and saved list/detail shape. No paid providers, frontend tests or browser automation. Frontend ESLint/TypeScript/fresh build and lifecycle source review remain required.
- Update backend database/API/deployment/image-retention specs plus frontend workspace/style-experiment specs: supersede browser-close-stops-run, first-GET seed latch and stop-on-one-failure rules. Existing saved endpoints and image seven-day retention are preserved.

### External references

No new dependency or external API is required. Reuse the pinned Python 3.12 runtime, SQLite transactions and existing MCP provider. The exact browser parser/arithmetic source is the parity authority. No live NovelAI call or external documentation was used for this research.

## Caveats / Not Found

- No durable scheduler/table exists in the inspected code; metadata-based saved experiments cannot themselves provide cursor, Stop state or safe paid resumption.
- Source is changing in parallel. Above types are the parent-aligned interface recommendation; parent owns final contracts and implementation ownership.
- One-second failed-group pacing, handling queue saturation as wait vs failed group, and the optional same-owner ordinary-generation block are explicit design choices requiring implementation consistency, not properties of existing code.
- Replaying a SQLite snapshot of an active run on a second/provider-enabled process can spend again even with per-database exactly-once claims. Recovery drill and rollback must keep schedulers/provider calls disabled until explicitly activating the authoritative state.
