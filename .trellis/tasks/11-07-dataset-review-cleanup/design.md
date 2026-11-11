# Training-set review and discarded-image cleanup design

## Boundaries and current behavior

The change spans saved-result navigation, thumbnail review, the authenticated API,
SQLite metadata, private result storage, and preview/cache lifecycles. It remains
one task because the default browser entry and safe purge need an integrated
review of the same image identities; separate deliverables would not reduce risk.

`SavedResultsStore.openExperiment` currently calls `loadGroup`, which immediately
fetches a full PNG. `SavedResultViewer` owns a separate, initially empty `gridFor`
state. `ReviewGrid` pages metadata and creates tiles by original image index.

The result-store protocol currently exposes only whole-job deletion.
`DiskResultStore._result` validates every file before serving any member, so merely
unlinking one image would break its retained siblings. Generation views currently
construct a dense URL array from `ResultInfo.image_count`. These identities must
remain stable when a member is removed.

## Navigation and default filter

Make grid/single mode selection-owned state in `SavedResultsStore`, rather than an
uncoordinated viewer-local default. Resolve a dataset from trusted list metadata
or the first accepted experiment summary, choose grid on each explicit dataset
open, and suppress the initial full-PNG fetch. Ordinary history and style
comparisons keep their current viewer behavior. Explicit full-image open switches
to single mode and loads exactly the selected original index. Returning to grid
releases/cancels unnecessary foreground image ownership.

Set the thumbnail grid's initial hide-discarded state to true. Keep its checkbox
and temporary user choice while that grid instance is open.

## Durable purge metadata and storage

Add schema 13 with an owner/job/image-index purge table, cascading with the job.
Each row records request time and whether physical file cleanup completed. Keep
the existing discard row: ordinary discard remains reversible until purge is
requested. Purge intent is durable before filesystem removal, so restore and all
image-serving paths can reject a purged identity even after partial failure or
restart. A subsequent explicit cleanup retries unfinished physical removals.

Expose additive `GenerationView.purged_images` and
`GenerationView.purge_pending_images` index arrays (batched for pages). Existing
`image_urls` indexes and the original generation image count remain stable;
historical counts describe generation output rather than current disk availability.
Consumers omit purged indexes instead of compacting the array. Pending indexes
remain purge targets but are unavailable for serving/restore.

Extend `ResultStore` with owner-scoped per-image removal for both memory and disk
implementations. Memory removal must release that member's bytes while keeping
the original slots of retained siblings. Disk removal uses an atomically replaced,
bounded manifest with validated deleted-slot metadata; old manifests without that
field stay readable. Publish the deletion marker before unlinking that member,
skip intentionally removed members in sibling validation, preserve original
expiry, use existing no-follow directory-relative filesystem operations and 0600
files, and never decode/re-encode remaining images. Retry must still unlink a
member whose manifest was already marked before a previous unlink failure.

Do not replace the whole result, reset its expiry, or remove its generation job.
Concurrent reads may fail closed; committed tombstones prevent later cached
previews or originals from exposing deleted identities. Check tombstones before
and after potentially long preview rendering. Evict affected preview entries.

## API and transaction flow

Add authenticated, Origin-protected
`DELETE /api/style-experiments/{experiment_id}/discarded-images`.
The request has no prompt/image payload. Owner/experiment-kind checks precede
mutation: 404 for missing/foreign sets and 422 for a non-dataset experiment.

1. In a short immediate transaction, resolve the owner's current set and snapshot
   all succeeded discarded image identities (including re-runs and unfinished
   earlier purge requests) without selecting prompt/caption content. Persist purge
   intent atomically. A concurrent restore either commits first and removes its
   target from this snapshot, or is rejected after tombstoning.
2. Remove each target's stored bytes, evict its previews, and mark successful or
   already-missing cleanup complete. Do not hold a SQLite transaction during all
   filesystem work. Concurrent cleanup requests must be idempotent.
3. Return typed aggregate `deleted_images`, `missing_images`, and `failed_images`
   counts. Count a physical removal only after confirmed success; report partial
   failures and leave their pending metadata for explicit retry. Storage failures
   must not become an all-success message. Keep errors free of private content
   and paths. New discards made after the snapshot wait until the next click.

The restore route atomically refuses purged indexes with 409 `image_purged`.
Original and thumbnail routes return the existing safe 404 for purged identities.
Cover selection excludes a purged first image. Generation views batch purge
lookups just like discard/caption lookups. Review the deterministic OpenAPI
snapshot and TypeScript client for every changed public field/error.

## Cleanup interaction and consumers

Place `清理已弃置图片` in the current set's review toolbar. Explain that it covers
this entire set regardless of selection, category, search, or pagination. Confirm
the set name (or unnamed fallback), target count, and irreversible deletion.
If metadata stops at the grid's existing group cap, label the known target count
as a lower bound; the cleanup endpoint still covers the entire set.
Disable duplicate/conflicting actions while cleanup is pending; cleanup never
queues paid work. Zero-target cleanup remains safe.

After any accepted cleanup outcome, reload review metadata, drop deleted
selections/edit targets, clear obsolete thumbnail URLs, and invalidate saved-viewer
full-image/preload caches. Refresh the saved list/cover metadata using existing
session guards. Preserve set/filter context. Report partial failure with an
explicit retry path, including when only pending purges remain.

The history panel can also resume a dataset job into `GenerationStore`, whose
full-PNG result remains mounted behind the saved viewer. Compose the cleanup
callback at `AppStore` so it invalidates a matching terminal dataset result before
and after cleanup, including an uncertain transport outcome. `GenerationStore`
must filter purged slots when loading results and release previously cached
purged URLs. Do not cancel queued/running paid work, clear an unrelated manual
result, or mutate the generation draft.

Update grid tile/quick-pick creation, viewer navigation/restore controls, preload,
and export loops to omit purged slots. A succeeded group with no retained image
must not become a fake failed tile or a re-run target merely because all its
images were purged. Keep existing expired/failed placeholders truthful.

## Compatibility, rollout, and rollback

The schema migration is additive and preserves old discard/caption/job data.
Old disk manifests remain compatible. Deploying is outside this task; when the
operator deploys later, migrate/run the API before publishing the matching web
bundle. Rollback must preserve purge markers and compatible storage readers:
rolling back to an old API that ignores tombstones is unsafe if physical cleanup
is still pending. Permanent file deletion has no application undo. Backups and
operator-exported copies are outside cleanup scope.

## Privacy and validation

Use only repository source/specs and synthetic files/disposable databases. Never
read real training/reference images, captions, dataset prompts, SQLite rows, or
exported archives. No live browser probes against private sets and no paid calls.
Use synthetic multi-image/re-run/owner fixtures to verify precise file deletion,
index stability, restart, migration, missing files, partial failure, concurrent
restore, thumbnail eviction, and retry. Static frontend review, lint/type-check,
and an env-free staged production build verify browser code; real interaction is
operator acceptance.
