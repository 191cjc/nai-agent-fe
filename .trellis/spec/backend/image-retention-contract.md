# Private Image Retention and Experiment History

## Scope / Trigger

Use for generated result storage, capacity admission, generation metadata,
private image routes, saved experiment comparisons or state-directory rollout.
The operator removed automatic seven-day image expiration on 2026-11-12.
Server-private disk images remain until explicitly deleted. This supersedes
the former seven-day policy; SQLite still contains no PNG.

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

- Retain valid images until explicit deletion, including existing images whose
  version-1 manifests contain the former `saved_at + 604800` expiry. New
  manifests use `expires_at: null`; disk results expose `result_expires_at: null`.
  Never use stored expiry or directory age to delete or hide completed results,
  including corrupt result directories. Do not rewrite legacy manifests.
  Startup, periodic and admission sweeps reclaim only abandoned managed
  `.tmp-<uuid>` directories and `.reserve-<uuid>` files (one-hour age outside
  startup). The injected in-memory test cache retains its separate short TTL.
  Existing legacy records without bytes remain reusable parameter history.
- Private directories 0700/files 0600, safe UUID paths, bounded manifests,
  no symlink following, exclusive temp writes and atomic publication. Preserve
  existing PNG/count/per-image/per-result validation. Missing/corrupt artifacts
  fail safely without paths/prompts/credentials in errors. Cleanup deletes only
  explicitly selected result UUIDs or abandoned temp/reservation names; preserve
  unknown artifacts and include their bytes in capacity accounting. Reject
  unbudgetable nested trees safely.
- No fixed store budget by default (2026-11-04); admission keeps at least 3 GiB
  free disk. An explicit budget is still honoured. Reserve worst-case accepted output
  min(sample_count*8 MiB,32 MiB) before paid admission; include all pending
  reservations. Do not evict saved images to admit new work. Release on
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
- Images and history/experiment metadata remain until explicitly deleted.
  Explicit terminal history deletion removes its files and group association. Foreign jobs,
  images and experiments return 404. No public static image route exists.
- Construction/OpenAPI creates neither storage files nor DB. Storage lifecycle
  belongs to startup/shutdown; no credentials/provider calls in schema probes.
- SQLite backup excludes PNG bytes. Disk store is separate private state;
  retain it across release switches, and document separate backup needs.

## Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Stored result after process restart | Same authenticated image bytes, no expiry |
| Seven days elapsed, including legacy manifests | Images and parameters remain available; no automatic result deletion |
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

Use disposable files/SQLite and fake providers only. Assert new and legacy
images survive past the former expiry across restart, periodic and admission
sweeps; abandoned temporary files are still reclaimed. Check private modes/safe
paths, corrupt/missing artifacts,
owner isolation/deletion, reserved capacity under concurrency/cancel/shutdown,
pre-admission refusal, exact grouping/metadata bounds, duplicate prevention,
huge ordinal sort/pagination and unchanged flat/native provider arguments.
Full frozen offline pytest/Ruff/lock and deterministic reviewed OpenAPI apply.
Frontend uses static/source review and env-free build; no browser/helper tests
or paid generation/advice. Real operator interaction stays a separate gate.

## Wrong vs Correct

- Wrong: honor old expiry, delete old result directories, or scan/create private
  state during
  create_app(...).openapi().
- Correct: retain old/new results without rewriting manifests and initialize
  storage only in lifespan; reap only abandoned temporary artifacts.
- Wrong: reload a saved experiment by resubmitting its generation requests.
- Correct: page saved jobs and fetch existing images through owner-auth routes.

## Grid-review previews (2026-11-03)

- `GET /api/generation-results/{job_id}/images/{image_id}/thumbnail` →
  `image/webp`, long side ≤384 px (never upscaled), quality 80, `no-store`,
  `nosniff`. Same rules as the full PNG: owner-only (404 otherwise), job
  `succeeded`, retained original present (`describe`), index in
  range; 401 without a session.
- `thumbnails.ThumbnailCache`: memory-only LRU keyed by `(job_id, index)` and
  bound to the owner, 32 MiB total. Nothing is written to the result
  directory, so retention sweeps, budgets and lock-free reads are unchanged.
  Original image identities never change in place; explicit
  [per-image purge](./dataset-review-contract.md) can remove a slot without
  renumbering siblings. Every hit is gated by current result metadata and purge
  intent, and successful job deletion or per-image purge evicts affected previews.
- Rendering: Pillow, PNG only, ≤2048×2048 source pixels checked before
  decoding; a fresh image is saved so no PNG text/ICC/EXIF survives. At most
  2 concurrent renders; a request that waits 20 s returns 503
  `thumbnail_busy` (retryable, never a paid action).
- Tests: `tests/test_thumbnails.py`.
