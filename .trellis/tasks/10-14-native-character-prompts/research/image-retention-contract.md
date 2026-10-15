# Research: Private image retention and saved style comparisons

- Query: Retain generated images privately for seven days, including across page refresh and API restart; recover style comparisons without resuming paid work.
- Scope: internal source inspection and local, disposable SQLite capability probe; no provider calls or production inspection/writes.
- Date: 2026-10-15

## Findings

### Existing files and contracts

| File | Relevant responsibility |
| --- | --- |
| `apps/api/src/novelai_api/generations.py` | Request/history models, owner job store, memory image cache, bounded executor. |
| `apps/api/src/novelai_api/app.py` | Cache injection, startup/shutdown, owner-authenticated image routes and deletion. |
| `apps/api/src/novelai_api/db.py` | Explicit schema migration, private SQLite access and DB-only online backup. |
| `apps/api/src/novelai_api/migrations/0002_generations.sql` | Existing `settings_json` column and owner/time index; no image columns. |
| `apps/api/src/novelai_api/config.py` | `sqlite_path` and provider configuration; no image-directory or retention setting today. |
| `apps/api/src/novelai_api/mcp_images.py` | Explicit provider argument mapping; application-only experiment metadata can remain outside its payload. |
| `apps/web/src/api.ts` | Typed JSON requests and protected PNG-to-Blob fetch. |
| `apps/web/src/store.ts` | Generation operation ownership, browser experiment scheduler, URL ownership and parameter-only history. |
| `apps/web/src/style-experiment.ts` | Exact Cartesian plan, arbitrary-precision totals/ordinals and labeled per-group weights. |
| `apps/web/src/StyleExperiment.tsx` | Experiment controls and single-image arrow comparison viewer. |
| `apps/web/src/App.tsx` | History drawer and ordinary result display. |
| `apps/api/tests/test_generations.py` | Existing fake-provider, injected cache clock, restart, deletion and capacity regression coverage. |
| `apps/api/tests/test_api_contract.py` | Exact OpenAPI snapshot and constructor-without-side-effects guarantees. |
| `deploy/novelai-api.service` | One API worker, private state directory, writable path limited to `/var/lib/novelai`. |

Current behavior:

- `generations.py:19-22` caps one PNG at 8 MiB, one result at 32 MiB, cache at 64 MiB, TTL at 600 seconds. `ResultCache.put` (`:243`) validates the entire result then evicts the earliest deadline when capacity is needed (`:264`). `get` (`:277`) prunes on access. Images are process-only tuples of bytes (`:227`); there is no filesystem persistence.
- `GenerationRequest` (`generations.py:49`) is serialized in full into `settings_json` by `JobStore.create` (`:130-144`) and validated back by `_item` (`:214`). Additive defaulted metadata therefore needs no SQL migration. Existing history input compatibility must remain intact.
- `HistoryItem` contains parameters and generated `image_count`; `GenerationView` adds `image_urls` and `result_expires_at` (`generations.py:105-118`). Preserve these field meanings: produced count remains after expiration, URLs reflect currently available results.
- `app.py:311-324` derives links from the cache; `:337-355` authorizes the owner job before returning PNG bytes with `no-store`, `nosniff` and a fixed safe filename. `:369-385` deletes the owner job before discarding the cached result; active jobs return 409.
- `GenerationManager.start` marks queued/running jobs interrupted; `stop` waits for running work and cancels queued futures (`generations.py:316-324`). Paid work remains single-threaded with three accepted slots (`:313`, `:319`). Results are stored before job success (`:350-354`), and failed transitions discard images.
- The current browser archive has no durable ID. `StyleExperimentRun` and `StyleExperimentResult` (`store.ts:204-220`) contain bigint ordinal/total, labeled weights, each job and its loaded Blob URLs. `ExperimentExecution` snapshots all parameters including character x/y (`:223-228`, `:409-414`). `advanceExperiment` rebuilds each weighted request (`:453-481`), and `finishOperation` archives images before scheduling the successor (`:604-632`).
- `store.ts:580-600` fetches all images of the current group as Blobs; `:610-614` transfers URL ownership to its archive row. Clear/new run/logout dispose local URLs (`:434-444`, `:664-683`). Persistent server retention should not change these ownership rules for a live run.
- Successful history cannot currently be reopened from the drawer: `App.tsx:385-389` offers only reuse, plus status inspection for queued/running rows. `GenerationStore.resume` (`store.ts:686`) can already retrieve a terminal ordinary job, but the UI does not invoke it. A success-image entry point is required even for the minimal persistence feature.
- `AppStore.enterWorkspace` (`store.ts:933-946`) automatically restores parameters only, guarded against concurrent edits. Do not turn this into generation or paid-run resumption.
- Existing comparison arrows flatten all rows/images already held in memory (`StyleExperiment.tsx:161-180`); unavailable rows occupy a placeholder. Arrow movement is currently synchronous and makes no requests. A saved paginated comparison needs a deliberately separate lazy loading path, preserving live-run navigation semantics.

### Recommended application metadata and response shapes

Minimal additive request field (absent/null for ordinary generation):

```json
{
  "style_experiment": {
    "id": "e1d29d44-7b47-4798-b462-16c0a22257fc",
    "ordinal": "1",
    "total": "9",
    "weights": [
      {"tag_index": 0, "label": "artist:example", "weight": "0.8"}
    ]
  }
}
```

- Generate one UUID at valid explicit Start and freeze it with the plan. Ordinal is one-based. Save this field with every accepted group; it is application metadata, never an MCP argument. The adapter already constructs its exact payload explicitly (`mcp_images.py:216-242`).
- Total and ordinal must be canonical positive decimal **strings**, with ordinal <= total. Browser plans intentionally use bigint without a total-combination cap (`style-experiment.ts:59`, `:68-87`). Do not convert these to a JS number or SQLite INTEGER/REAL. If adding a finite metadata-text limit (e.g. 4096 digits), reject too-large plans explicitly before the first POST; never silently truncate the experiment.
- Weight preserves the exact decimal string already produced by `styleExperimentCombination` (`style-experiment.ts:91-106`), including neutral `1.0`; tag index identifies occurrences, not unique text. Bound metadata: UUID format, nonempty unique occurrence indices, max selected occurrences consistent with the 3000-character source, label/weight text lengths and aggregate byte size. Do not trust client labels for HTML or SQL.
- Original range/source metadata is unnecessary for viewing old comparisons: each job already saves its weighted style, frozen settings, seed and characters. Add range/source only if re-editing a saved experiment becomes a separate explicit requirement.
- Ordinary reuse must strip `style_experiment`: `reuse` currently spreads all `item.parameters` (`store.ts:350-360`). Likewise `GenerationDraft` currently derives directly from GenerationRequest (`:42`), so adding the API field blindly risks treating a reused ordinary generation as a member of the saved experiment. Exclude it from draft type and build it only in the live experiment path.

Suggested endpoints (parent owns final naming):

```text
GET /api/style-experiments?limit=20&offset=0
  {items: [{id, created_at, updated_at, total: "9", submitted_count: 3,
            image_count: 6, queued_count: 0, running_count: 0,
            succeeded_count: 3, failed_count: 0}], next_offset: null|number}

GET /api/style-experiments/{id}?limit=20&offset=0
  {id, total: "9", items: GenerationView[], next_offset: null|number}
```

- Parameter-only list/history remains small; detail supplies metadata/URLs, not PNG payloads. Require owner session on both. Unknown or foreign IDs return the same 404; list filters owner **before** grouping, even if two users send the same experiment UUID.
- Count only actually accepted rows. Do not call `submitted_count < total` "running" or claim "stopped": the server cannot distinguish browser closure, Stop, failed POST or a second tab from these rows. Use read-only saved-group counts and actual job statuses; live browser status stays in the scheduler.
- List sort: newest owned group's time/id descending, grouped deterministically. Detail sort: canonical ordinal by `length(ordinal), ordinal`, then created_at/id tie-breaker. Numeric `CAST` corrupts bigint ordering beyond SQLite integer precision. Define duplicate ordinal behavior: minimally show both saved jobs with stable tie-breakers; never interpret archive recovery as permission to resend.
- Reuse existing `limit` 1..100 and JavaScript-safe offset validation. Limit+1 enables next-offset paging without loading every group. Keep group parameters even after images expire or a group fails.
- A saved comparison should fetch only its metadata page and current image/current group, owning a small bounded number of Blob URLs. Avoid eagerly loading all seven days of images back into browser memory. Page navigation may fetch saved data but must never call `submit`, recreate `execution`, acquire the generation-operation lock, or auto-continue a paid plan.

### SQLite JSON support

- Local system Python and `apps/api/.venv/bin/python` both report SQLite **3.45.1**. An in-memory query confirmed `json_extract('{"style_experiment":{"id":"x"}}', '$.style_experiment.id') = 'x'` and `json_valid('{}') = 1`. No DB file was opened by this probe.
- The existing table stores JSON as TEXT without a JSON CHECK; current writes use Pydantic JSON. Owner-scoped `json_extract(settings_json, '$.style_experiment.id')` works without a migration/index, but grouping scans that owner's records (the owner index still helps). Treat this as the minimal bounded approach and document the scale limit; an indexed dedicated experiment table is a future optimization.
- Prefer guarded extraction (`CASE WHEN json_valid(settings_json) THEN json_extract(...) END`) if supporting manually imported/corrupt legacy JSON. Ordinary `_item` already cannot parse corrupt records; do not inadvertently make an archive listing for one bad row a new global failure.
- Production SQLite runtime capability was not queried. Verify JSON availability in the staged runtime without touching live data; do not infer it solely from system `sqlite3` CLI.

### Recommended disk result contract

- Default root beside the resolved SQLite file, e.g. `database.path.parent / "generation-results"`, keeps images outside releases/web root and within the current unit's writable `/var/lib/novelai` (`deploy/novelai-api.service:14-29`). Avoid new environment wiring or unit changes unless needed.
- New job directory mode 0700; manifest and PNGs mode 0600, independent of ambient umask. Use server-generated UUID paths and reject unsafe/symlink entries. Never expose filesystem paths, prompt text or credentials in manifest responses/errors. Keep authorization grounded in the owned DB row plus stored owner, not just an unguessable filename.
- Persist immutable `stored_at` and `expires_at = stored_at + 604800` wall-clock seconds in a bounded sidecar manifest, with owner, image count/sizes and fixed PNG filenames. Viewing does not extend retention. A monotonic deadline cannot survive process restart; injected wall time is needed for restart/expiry tests.
- Validate all existing PNG/count/byte rules first. Write all images and manifest into a private temporary directory, flush, then atomically publish the result directory. Never publish a partial group. Failed writes leave job failure and no accessible partial result. Keep the current store-before-success ordering; startup reconciliation removes abandoned temp/orphan results when the DB job is absent/failed/interrupted.
- Keep metadata inspection separate from loading PNG bytes: `describe(job_id,user_id) -> {image_count, expires_at}` and `read_image(job_id,user_id,index) -> GeneratedImage|None` avoids reading up to 32 MiB merely to list URLs. Existing `cache.get(...).images` (`app.py:315-320`, `:341-348`) would otherwise cause a saved detail page to load many groups into RAM.
- Expiration denies access immediately at the persisted deadline, returns no available URLs and null expiry in the existing view shape, and returns indistinguishable 404 for image reads. Preserve succeeded status, original image_count, parameters and experiment metadata. Cleanup deletes bytes, not history.
- Delete one terminal history job removes its files too; missing/already expired files are idempotent. Active-job 409 and owner checks remain. Define retries/maintenance for the existing DB-first delete ordering so a filesystem unlink error cannot leave unbounded inaccessible orphans.
- Run startup and periodic cleanup, not access-only cleanup: otherwise an idle server retains private bytes forever after seven days. Strict read-time expiry still applies between cleanup ticks. Restrict maintenance to managed paths; do not recursively remove arbitrary state-directory siblings. Cancel/join maintenance during shutdown after provider settlement.

### Capacity and lifecycle edges

- Seven-day retention conflicts with the old capacity eviction policy. Recommend retaining all unexpired accepted results and refusing **new paid work** when capacity/free-space reserves cannot accommodate it; never silently evict yesterday's test images.
- Use a documented configurable disk budget (parent chooses from host capacity). Before seed assignment/history/enqueue/provider invocation, reserve `min(sample_count * MAX_IMAGE_BYTES, MAX_RESULT_BYTES)` bytes plus a small filesystem safety margin. Count accepted queued reservations and existing files. Release excess reservation after actual write; release on validation/provider failure, enqueue error and cancellation. Low free space is separate from logical budget. Return an explicit typed refusal such as `503 image_storage_full` before any paid call; frontend may classify only the verified exact pair as definite refusal, preserving all other uncertain outcomes.
- Do not discover capacity failure only in `put` after the paid result exists. A disk failure can still happen despite preflight; surface a secret-free terminal `image_storage_error`, halt experiments and never auto-retry generation.
- Critical cancellation detail: `_run` releases only when it executes, while `stop` uses `cancel_futures=True` (`generations.py:323`). Queued canceled futures never execute `_run/finally`; reservations need cancellation/enqueue-failure handling or a manager-owned stop cleanup. Do not leak reservations or reuse stale counts after manager restart.
- `create_app(...).openapi()` must not create directories/scan/delete images: `test_api_contract.py:16-39` explicitly checks construction side effects. Perform store initialization/maintenance in lifespan/start (`app.py:115-124`), and keep disposable injected stores supported (`create_app(result_cache=...)`, `test_generations.py:85-94`). Prefer an explicit result-store protocol if retaining the old memory test double; avoid truthiness fallback if an empty store implements `__len__`.
- SQLite-only backup remains metadata-only and should still contain no PNG bytes. A separate image root is not included in `Database.backup`; document that DB restore alone cannot restore pictures. Restart durability uses the unchanged image root. Do not automatically purge unexpired images because a temporary recovery/drill DB lacks rows unless that store root belongs to the drill.

### Offline regression coverage to change/add

1. Replace default "restart loses pictures" assertions (`test_generations.py:314-353`) with exact same PNG/expiry after a new API instance and same persisted root. Preserve a separate memory-store-injection test if retained.
2. Inject wall clock; verify available at just before seven days, unavailable at boundary/after restart, no sliding extension, unchanged history/metadata. Existing TTL test at `:449-461` is the baseline.
3. Owner isolation for disk PNG, ordinary history, experiment list/detail; revoked session and wrong Origin on delete; same experiment UUID across users; safe path/symlink/malformed manifest handling and no secret/path leakage.
4. Private file modes under permissive umask, immutable atomic whole-result writes, startup cleanup of incomplete writes, idempotent deletion, filesystem errors without partial accessible output. Preserve bad PNG/count/byte validations (`:464-511`).
5. Replace eviction test (`:515-536`) with capacity refusal **before** random seed, job persistence, enqueue/provider work; old unexpired PNG remains. Verify reservations with queued jobs, provider errors, enqueue failure and canceled futures; storage write failure is terminal and not retried.
6. Save/restart/page experiment groups with exact weights, UUID, huge decimal totals/ordinals, failed/expired group placeholders; ordinary/legacy rows excluded; stable ordering/pagination beyond page one; malformed metadata rejected without a provider call.
7. Preserve frozen seed/settings/character x/y in every saved group, metadata absent from MCP's exact provider arguments, ordinary request/reuse not accidentally grouped, and backup bytes containing no PNG. Metadata-only restore should not imply restoration of the separate result directory.
8. Refresh OpenAPI snapshot and expected protected-route errors, assert no constructor-created DB/image directory, document any explicit definite storage refusal. Full backend offline pytest/Ruff/lock checks. Frontend verification remains source lifecycle review plus ESLint/TypeScript/fresh env-free build; no frontend automated tests or browser automation.

### Related specs and external references

- `.trellis/spec/backend/api-contract.md`: presently describes transient owner image links and parameter-only history; update retention/archive contracts and specific pre-acceptance refusal boundary.
- `.trellis/spec/backend/database-guidelines.md`: preserve no PNG in SQLite; replace process-memory-only description and clarify separate image backup boundary.
- `.trellis/spec/backend/deployment-contract.md`: replace restart-loses-images premise; document stable private image root/capacity/cleanup while keeping current env, unit and Nginx unchanged.
- `.trellis/spec/frontend/workspace-contract.md`: preserve auth/session cleanup, entry restoration guards and exact uncertain-submit semantics; add historical-image viewing and metadata stripping on reuse.
- `.trellis/spec/frontend/style-experiment-contract.md`: change browser-only archive assumption, keep browser-only sequential scheduler/no auto-paid-resume, separate live URL archive from lazy saved viewer.
- No external provider documentation is needed for these changes: the provider request shape and paid-generation scheduler remain unchanged. Local Python SQLite runtime is the only directly probed capability.

## Caveats / Not Found

- No durable experiment IDs, experiment endpoints, disk image root, periodic retention worker or capacity preflight exists in the inspected code.
- Seven days applies prospectively to images successfully saved by the new store. Previously expired/restarted-away memory bytes cannot be recovered.
- Current browser Stop/closure is not saved to SQL; a read-only archive cannot truthfully reconstruct the original live-run outcome or authorize automatic continuation.
- Current live experiment still loads all completed group PNGs into browser memory. Server durability fixes recoverability, not live-run RAM growth; use a separate bounded lazy saved viewer without rewriting the paid scheduler unless explicitly scoped.
- No production free-space/budget, production Python JSON capability or browser acceptance was checked. Parent chooses final capacity and interface; all shapes here are recommendations, not an already implemented API.
