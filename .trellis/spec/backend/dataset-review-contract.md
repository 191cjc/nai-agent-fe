# Dataset Review Defaults and Permanent Image Cleanup

## Scope / Trigger

Use when changing saved training-set entry, discard filtering, permanent cleanup,
individual result slots, or the original/thumbnail/export/cache consumers of
deleted images. Reversible discard and permanent purge are separate actions.
The operator selected cleanup of the currently opened training set only.

## Signatures

- `DELETE /api/style-experiments/{experiment_id}/discarded-images` takes no
  body and returns `{deleted_images: int, missing_images: int, failed_images: int}`.
- `GenerationView.purged_images` and `purge_pending_images` are sorted original
  image-index arrays, default empty. Pending purge indexes are also purged and
  unavailable; their physical cleanup can be retried.
- Schema 13 (`0013_purged_images.sql`) adds
  `purged_images(user_id, job_id, image_index, created_at, completed_at)`, keyed by
  owner/job/index and cascading with a deleted generation job. NULL `completed_at`
  means physical cleanup is pending. It contains no image/prompt/caption content
  and never changes the frozen generation request.
- `ResultStore.purge_image(job_id, user_id, index) -> bool` removes one original
  slot: true means bytes were removed, false means they were already absent;
  storage errors raise rather than returning false. Disk manifest v1 gains an
  optional validated `deleted_images: list[int]`, defaulting to empty.
- `SavedResultsStore(api, onDatasetCleanup)` receives its callback from `AppStore`.
  It calls `GenerationStore.invalidateDatasetResult(experimentId)` before cleanup
  and in `finally`, even when the saved-view selection has closed or changed.
- Original PNG and thumbnail routes keep their existing signatures and safe 404
  behavior for purged indexes. Restoring a purged discard is refused with
  `409 image_purged`.

## Contracts

- Each explicit saved-dataset open selects thumbnail review and initially checks
  `隐藏已弃置`. Cover and browse actions share this behavior. Resolve the dataset
  from accepted owner metadata before fetching a full PNG; changing the default
  view must not briefly download an original. Single-image review stays explicit.
- A grid instance belongs to one open lifetime, including repeated opens of the
  same set. `SavedResultsStore.selectionVersion` advances on close/open teardown;
  key the grid by both set ID and that version. A key of set ID alone can retain
  old checkbox/selection state and accept late cleanup callbacks after reopening.
- The cleanup button covers all discarded indexes of the current set, including
  re-runs, all pages, hidden tiles, and images outside the current search/category.
  It is independent of selection. Confirm the set name/fallback, count and
  irreversible effect before issuing the mutation. Cancel sends no request.
  If the grid's bounded metadata read is incomplete, label the displayed target
  count as a lower bound; the server still cleans the entire current set.
- Atomically snapshot targets and persist purge intent before file removal.
  Concurrent restore either commits before that snapshot and survives, or is
  refused after tombstoning. New discards after the snapshot wait for another
  cleanup. Keep SQLite write transactions short; do not hold one across a whole
  batch of filesystem work. Repeated cleanup is idempotent.
- Physical removal releases only the discarded member's bytes, preserves sibling
  bytes and original indexes, and retains the original expiry. Existing disk
  manifests remain readable. Intentionally removed slots are distinguished from
  corrupt/missing retained slots; never compact file names or URL arrays.
- Count success only after physical removal is confirmed. Already missing bytes
  count separately. A failed removal remains durably pending and unavailable;
  an explicit retry can finish it after refresh or restart. Never silently report
  all-success while a marked file still exists.
  Viewer counts and the current-image placeholder distinguish completed purges
  from pending physical cleanup; purge intent alone is not completed deletion.
- Every original read, thumbnail cache hit/render completion and restore is gated
  by durable purge metadata. Evict affected thumbnail entries. Purged original
  indexes remain unusable after restart and cannot be exposed by stale previews.
- `image_urls` retains original slot indexing; historical `image_count` continues
  to describe generated output. Consumers explicitly skip purged indexes: grid
  tiles, selection, quick picks, navigation, preload, restore, and export. A group
  whose successful images were all purged is not a failed/re-run placeholder.
- Refresh review and list/cover metadata after accepted cleanup outcomes, drop
  deleted selections/edit targets, revoke obsolete thumbnail/full/preload URLs,
  and guard against late responses after close/logout/selection replacement.
  Preserve the current set/filter context and show a retry when pending purges
  remain, including when no visible tiles remain.
- History can resume a dataset job into the ordinary `GenerationStore`, whose
  result remains hidden behind the saved viewer. Revoke that result's URLs before
  and after cleanup only when its dataset ID matches and it is terminal, not busy,
  and has no active job. Invalidate late image reads through its existing epoch;
  never stop/clear a queued/running paid job or an unrelated manual result/draft.
  Its image-loading path must also revoke and skip purged dense-array slots.
- Cleanup preserves parameter history, names, captions, run state, references,
  snapshots, unmarked siblings and other sets/owners. It invokes no generation or
  advice. Existing backups and exported copies are outside its scope.

## Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Missing/invalid session or wrong/missing mutation Origin | Existing 401 / 403 |
| Missing or foreign set | Safe 404, no mutation |
| Owned non-dataset experiment | 422, no cleanup |
| Current set has no cleanup targets | Zero counts; no other data changed |
| Marked image already expired/missing | Missing count; no retained sibling deleted |
| Some file removals fail | Truthful failure count; durable pending retry |
| Restore after purge intent | 409 `image_purged` |
| Original/thumbnail after purge | Safe 404, including cached preview |
| Repeated cleanup / process restart | No resurrection, stable retained indexes |
| Cancel confirmation / switch view | No cleanup / no paid work |

## Good / Base / Bad Cases

- Good: discard image 1 of a three-image group, confirm current-set cleanup,
  and retain the exact original URLs/bytes of images 0 and 2. Image 1 cannot be
  restored; list/grid/export no longer offer it.
- Base: ordinary discard remains reversible until explicit permanent cleanup.
  Empty or already-cleaned sets return zero counts safely.
- Bad: delete a whole result directory for one discarded image, shift index 2
  into slot 1, serve a cached preview after purge, or interpret one successful
  unlink as complete success for a partially failed batch.

## Tests Required

Use `tests/test_purged_images.py` with synthetic fixtures, disposable SQLite/files
and fake providers only. Cover
partial multi-image cleanup, original index stability, all-purged groups, re-runs,
foreign owner/set isolation, missing/expired members, migration/restart, repeated
cleanup, failed unlink/manifest update with explicit retry, restore races, cached
and concurrent thumbnail serving, and no paid calls. Review/update deterministic
OpenAPI and the TypeScript consumer deliberately.

No frontend/helper/browser automated tests or live private-image probes. Use
independent source review, ESLint/TypeScript, and an env-free staged production
build. Operator interaction remains the final runtime acceptance.

## Wrong vs Correct

- Wrong: unlink one PNG using the old all-members-required manifest reader, or
  renumber surviving URLs and leave discard indexes pointing at different images.
- Correct: durable per-index purge intent, deliberate deleted-slot storage metadata,
  and preserved original indexes across storage, API, UI, and export.
- Wrong: inspect a real training set to verify cleanup or show it in a browser.
- Correct: prove file absence and sibling checksums using synthetic images only.

For a dense URL array, apply deletion state before rendering or fetching a slot:

```ts
const purged = new Set(job.purged_images ?? [])
const retained = job.image_urls.flatMap((path, index) =>
  purged.has(index) ? [] : [{ path, index }])
```

The retained index is the original one, not its position in the filtered list.
