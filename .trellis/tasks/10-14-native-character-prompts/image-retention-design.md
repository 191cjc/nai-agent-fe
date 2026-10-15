# Private Seven-Day Images and Saved Experiment Comparison

> Follow-up precedence (2026-10-15): `durable-experiment-design.md` now owns
> server scheduling, continuation, reattachment and schema3 migration. Earlier
> browser-only/no-resume/no-migration exclusions below are historical for that
> boundary. Private seven-day storage remains in scope.

## Approved Outcome / Boundary

The operator chose private server storage for seven days, surviving refresh and
service restart, after seeing the memory-only/24-hour/permanent alternatives.
This supersedes earlier no-image-persistence exclusions for this follow-up.
Save new ordinary/experiment images, preserve experiment grouping/weights/seed,
and expose authenticated historical viewing. Do not recover expired legacy
bytes, auto-resume/retry a paid run, add a server batch scheduler, public image
URLs, browser persistence, account changes or automatic character placement.
Main coordinates, documents/contracts/release; API implementer owns all API
code/tests/OpenAPI; web implementer owns all browser code. Preserve each other's
edits. No frontend/helper automated tests, browser automation or paid probes.

## Storage Contract

- Production default becomes a private disk result store under the SQLite
  directory, `generation-images/`, outside web/releases. It implements existing
  put/get/discard result semantics; retain injectable ResultCache for offline
  memory-cache regressions. Constructors/schema imports create no files/DB.
- Each completed image set expires seven days after save, using persisted wall
  time so restart never resets retention. Expired bytes are not served. Sweep
  expired/abandoned temp artifacts on startup and periodically while running,
  not only on a later request. Restart retains unexpired completed images.
- UUID job directories, safe regular files, directories 0700/files 0600,
  exclusive temporary writes and atomic completion; no user-provided paths or
  symlink traversal. Validate current PNG/count/per-image/per-result bounds.
  Store a bounded private manifest with owner/job/count/expiry; never return
  private paths or upstream errors. Missing/corrupt files yield safe unavailable
  images, never another owner's content. Avoid unbounded reads/list allocation.
- Default image budget 2 GiB, reserve at least 1 GiB free disk. Reclaim only
  expired data; never silently evict unexpired seven-day images. Before paid
  admission, reserve min(sample_count*8 MiB, 32 MiB) against disk/budget and all
  other pending reservations. Release unused/all reservations on success,
  rejection, provider/queue failure and shutdown. Expose a dedicated safe
  503/result_storage_unavailable refusal before seed/history/provider work if
  capacity/write preflight fails, distinct from uncertain submission errors.
  Storage failure after provider work remains a terminal job error, no retry.
- Existing owner-authenticated image GET/no-store and generation GET URLs stay
  unchanged. Delete history removes its files; no PNG bytes enter SQLite.
  Old parameter records without files remain reusable with unavailable images.
  SQLite online backups still exclude image bytes; document that image-store
  backup is separate and retain its directory during code rollout/fallback.

## Additive API and Metadata (No SQLite Schema Migration)

GenerationRequest adds optional `experiment: ExperimentContext | null = null`.
This workspace-only metadata persists in settings_json, never MCP arguments.
Browser GenerationDraft excludes it; ordinary submit and manual history reuse
must not inherit an old experiment identity.

ExperimentContext fields:
- `id`: UUID serialized as canonical string, generated once per valid Start.
- `ordinal`, `total`: canonical positive decimal strings (1–1000 digits), with
  ordinal <= total; no float/SQLite integer coercion. Values remain lazy BigInt
  on the browser; reject oversized metadata before first paid POST.
- `weights`: 1–1500 objects `{tag_index: int, label: str, weight: str}`.
  Unique tag_index in 0..2999; nonblank labels, aggregate label budget 3000;
  canonical signed decimal weight string (max 100 characters). Preserve exact
  displayed metadata, including neutral weights, independently of prompt text.
- Keep a run's total consistent, reject duplicate owner/id/ordinal before any
  paid call with 409/experiment_conflict. DB transaction owns duplicate check.
  Preserve existing queue capacity, not-configured refusal and uncertain-POST
  boundaries; do not broaden their exception catches.

Use verified SQLite json_extract on existing settings_json to query only
validated metadata, parameterized owner/id queries, stable sorted pages:
- GET `/api/style-experiments?limit=20&offset=0` ->
  `{items: ExperimentSummary[], next_offset: int|null}`.
- GET `/api/style-experiments/{id}?limit=1&offset=0` ->
  `{summary: ExperimentSummary, items: GenerationView[], next_offset: int|null}`.
- Summary: `{id, total, group_count, completed_count, image_count, created_at,
  updated_at}`. Counts refer to saved submitted groups/generated images;
  images may have expired. List newest first with a stable id tie-breaker.
- Detail owner-scoped 404, groups ordered by length(ordinal), ordinal, job id;
  never CAST large ordinals. GET detail reuses generation-view serialization
  for existing authenticated URLs/expiry. Pagination bounds match history.
- Expiry removes image files, not parameter/group metadata. Existing individual
  history deletion implicitly removes that group's association. No experiment
  creation endpoint or new schema/migration/table is required.

## Browser Workflow

- Once Start has validated the plan and every shared setting, create one run
  UUID. Each existing sequential POST carries frozen id/total plus current
  ordinal/weights. Keep first-effective-seed latching, coordinates, Stop,
  uncertainty lock and image URL ownership. Fresh Start gets a fresh identity.
  No automatic new request after refresh/logout/network failure/restart.
- History offers ordinary successful image viewing and a saved-experiment
  list with counts/date and an explicit compare action. Keep existing drawers
  mounted and parameter reuse/latest-entry behavior. Explicit history tool
  actions may fetch; ordinary sidebar switching still does not submit/reset.
- Saved comparison has an independent read-only store/viewer. Page group
  metadata (limit=1 is sufficient), fetch only the selected image on demand;
  avoid downloading a whole experiment into browser memory. Show exact weights,
  ordinal/total, seed, parameters, expiry/unavailable state and current download.
  Left/right traverse each group's images then the next actual saved group;
  failed/expired groups have one placeholder, preserving their parameters.
- Scope keys to the viewer, keep boundary buttons disabled, stable contain
  sizing and correct metadata/download selection. Viewing saved results never
  changes the draft or current generation/experiment owner. If requests race,
  last selection/session wins. Revoke only this viewer's URLs on replacement,
  close, reset/logout/401/disposal. Existing current-run URL ownership remains.
- State clearly that images are privately retained seven days; parameters last
  longer. Refresh can reopen saved comparison; no promise of restarting a batch
  or recovering previously expired images. Clear current comparison only clears
  its page view, not silently deleting saved server images.

## Verification and Publication

Backend offline coverage: private file modes/safe paths, validity/bounds,
restart round trip, exact expiry across restarts, periodic sweep, deletion,
capacity reservations/low disk/concurrent jobs and no paid admission on refusal,
missing/corrupt files, owner isolation, duplicate/invalid metadata, huge ordinal
ordering/pagination, group restoration and unchanged flat/native provider args.
Run full frozen offline pytest/Ruff/lock checks and reviewed OpenAPI. Web uses
ESLint/TypeScript and source review of all request/session/snapshot/navigation
paths only. Fresh explicit env-free locked web build; independent full-scope
check and read-only rollout review before committing/publishing.

API-first paired release after verified private online SQLite backup, zero
active job checks and a warning to download old transient images. No env/unit/
Nginx/credential edits or paid calls. Private storage lives in the existing
service-writable state directory. Verify startup/private modes, loaded API
OpenAPI, public exact asset hashes, readiness, neighboring health and retained
assets. Keep new API and private image store if web falls back. Old API ignores
experiment metadata and cannot serve stored images; do not downgrade after
publication. Existing schema version stays 2; no DB restore is needed.
