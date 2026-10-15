# Private Image Retention and Experiment History

## Scope / Trigger

Use for generated result storage, capacity admission, generation metadata,
private image routes, saved experiment comparisons or state-directory rollout.
The operator selected server-private image retention for seven days. This
supersedes older memory-only image contracts; SQLite still contains no PNG.

## Signatures

- Production results use `<sqlite parent>/generation-images/`, separate from
  release/web directories. Retain injectable in-memory ResultCache for tests.
- `GenerationRequest.experiment` is optional/null workspace metadata:
  `{id: UUID, ordinal: decimal string, total: decimal string, weights:
  [{tag_index: int, label: str, weight: decimal string}]}`. Never forward it
  to the provider; normal/manual reused requests have no experiment identity.
- Existing `GET /api/generations/{id}` and authenticated
  `GET /api/generation-results/{id}/images/{index}` expose owner-only results.
- `GET /api/style-experiments?limit=20&offset=0` returns a page of summaries.
  `GET /api/style-experiments/{id}?limit=1&offset=0` returns summary, paginated
  GenerationView items and next_offset. Summary fields: id, total, group_count,
  completed_count, image_count, created_at and updated_at.

## Contracts

- Retain new valid images seven days from save, with persisted wall expiry.
  API restart does not extend or lose that retention. Expired results are not
  served; startup and periodic cleanup reclaim expired/abandoned artifacts.
  Existing legacy records without bytes remain reusable parameter history.
- Private directories 0700/files 0600, safe UUID paths, bounded manifests,
  no symlink following, exclusive temp writes and atomic publication. Preserve
  existing PNG/count/per-image/per-result validation. Missing/corrupt artifacts
  fail safely without paths/prompts/credentials in errors. Cleanup deletes only
  managed UUID/temp/reservation names; preserve unknown artifacts and include
  their bytes in capacity accounting. Reject unbudgetable nested trees safely.
- Budget 2 GiB with at least 1 GiB free disk. Reserve worst-case accepted output
  min(sample_count*8 MiB,32 MiB) before paid admission; include all pending
  reservations. Do not evict unexpired images to admit new work. Release on
  success/failure/queue rejection/canceled future/shutdown; canceled futures
  do not execute _run/finally. Capacity/write preflight refusal is distinct
  503/result_storage_unavailable before seed/history/provider work.
- Duplicate owner/experiment/ordinal and inconsistent totals reject with
  409/experiment_conflict before provider work; transaction owns the check.
  Keep other POST failures uncertain. No storage operation retries paid work.
- Persist group metadata in existing settings_json; durable run state uses
  schema3 as specified in durable-experiment-contract.md.
  Ordinal/total are canonical positive strings, <=1000 digits, ordinal<=total.
  Weight list 1–1500, unique tag_index 0..2999, labels nonblank/aggregate<=3000,
  canonical decimal weight <=100 chars. Detail sorts length(ordinal), ordinal,
  job id rather than coercing to float/SQLite integer. List sorts newest first
  with id tie-breaker. Queries are parameterized and owner scoped.
- Expiration removes files, not history/experiment metadata. Explicit terminal
  history deletion removes its files and group association. Foreign jobs,
  images and experiments return 404. No public static image route exists.
- Construction/OpenAPI creates neither storage files nor DB. Storage lifecycle
  belongs to startup/shutdown; no credentials/provider calls in schema probes.
- SQLite backup excludes PNG bytes. Disk store is separate private state;
  retain it across release switches, and document separate backup needs.

## Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Unexpired stored result after process restart | Same authenticated image bytes and original expiry |
| Seven days elapsed | Image unavailable; automatic file cleanup; parameters remain |
| Disk/budget/write reservation unavailable before admission | 503/result_storage_unavailable; no seed/history/provider execution |
| Storage failure after provider work | Terminal safe error; never automatic retry |
| Duplicate ordinal or inconsistent total | 409/experiment_conflict before provider work |
| Invalid/oversized metadata | 422 before paid admission |
| Foreign/missing job/image/experiment | Safe 404 |
| Huge valid decimal ordinal | Exact length/lex order and stable bounded pagination |
| Cancel pending executor future | Release reservation even though _run never executes |
| Missing/corrupt private file | Safe unavailable image; no leaked filesystem path |

## Good / Base / Bad Cases

- Good: refresh after a 20-group experiment, open its saved comparison, and
  view exact parameters/weights/seed and retained image after API restart.
- Base: pre-retention job has parameters and no files; reuse works without
  pretending its image can be recovered.
- Bad: changing ten-minute TTL alone, evicting yesterday's image for new paid
  work, storing PNG in SQLite or exposing private files through Nginx.

## Tests Required

Use disposable files/SQLite and fake providers only. Assert seven-day expiry
across restart, cleanup, private modes/safe paths, corrupt/missing artifacts,
owner isolation/deletion, reserved capacity under concurrency/cancel/shutdown,
pre-admission refusal, exact grouping/metadata bounds, duplicate prevention,
huge ordinal sort/pagination and unchanged flat/native provider arguments.
Full frozen offline pytest/Ruff/lock and deterministic reviewed OpenAPI apply.
Frontend uses static/source review and env-free build; no browser/helper tests
or paid generation/advice. Real operator interaction stays a separate gate.

## Wrong vs Correct

- Wrong: rebuild expiry from startup time, or scan/create private state during
  create_app(...).openapi().
- Correct: save expiry once and initialize/reap storage only in lifespan.
- Wrong: reload a saved experiment by resubmitting its generation requests.
- Correct: page saved jobs and fetch existing images through owner-auth routes.
