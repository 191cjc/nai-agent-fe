# Saved Viewer Image Cache Contract

## Scope / Trigger

Use when changing SavedResultsStore navigation, authenticated PNG loading or
viewer/session cleanup. This supersedes earlier selected-Blob-only language
for saved generation and experiment comparisons. Ordinary generation image
ownership and server retention/scheduling are separate.

## Signatures

- SavedResultsStore owns a viewer-local cache keyed by the exact validated
  `/api/generation-results/{id}/images/{index}` path.
- WorkspaceApi.image(path, signal) still authenticates each miss and uses
  `cache: 'no-store'`. No HTTP disk cache, Web Storage or IndexedDB is added.

## Contracts

- Default browsing caches successful PNG Blob URLs: at most32 entries AND64MiB summed
  Blob.size. A hit refreshes LRU recency and avoids another image-byte request.
  These are compressed image bytes, not a bound on browser decoded memory.
- Continue normal group/generation metadata reads on navigation. A cache hit
  requires current accepted metadata exposing the same image path.
  `result_expires_at: null` means no server expiry; a numeric expiry must still
  be valid. Normalize null to Infinity only inside the bounded in-page cache,
  including explicit preloading. Do not cache metadata or extend numeric expiry.
- Prune expired entries on access. Evict least recently used entries until
  both budgets fit. Keep the displayed URL valid and include it in the budget;
  do not create a second Blob URL for a hit. A single oversized image can be
  displayed transiently but must not become an over-budget cache entry.
- The cache owns its URLs. Navigation releases the display reference; eviction,
  expiry or clearing revokes the cached URL. An uncached oversized image is
  display-owned and revoked when released. Failed loads/placeholders never
  enter the cache. Default browsing never prefetches neighbors or accumulates
  whole experiments; explicit bulk loading follows the exception below.
- Close, opening another selection, reset, logout start, 401 and dispose clear
  the cache and revoke its URLs. A refresh has no persistent cache to restore.
  Epoch/abort/session guards reject late reads before URL creation/cache fill.
- Keep image, index, metadata, filename and current download aligned. Navigation
  and cache cleanup never mutate the draft or stop/resubmit paid server work.
  Explicit result-seed clicks update only the draft seed under the workspace
  contract; local sanitized Save owns separate temporary export resources and
  never changes or revokes the cache's original URLs.

## Explicit Experiment Preload

### Scope / Signatures

The operator explicitly requested one button to begin loading all currently
saved experiment images. This is an exception to lazy-only viewing, triggered
only by an explicit experiment-viewer action; ordinary generations stay lazy.
SavedResultsStore owns preload state/epochs/controllers and all PNG URLs.
Its preloadImages(): Promise<void> and cancelPreload(): void actions expose
preloadStatus plus checked-group, processed-image, skipped-group and failed-image
counts; cachedImageCount/cachedImageBytes report current cache ownership.
Use existing WorkspaceApi.experiment(id,offset,limit,signal) and image(path,signal);
no API, server scheduler or provider changes.

### Contracts

- Read metadata in bounded20-group pages; freeze initial group_count as the
  pass boundary, so a growing server run cannot keep the pass alive indefinitely.
  Do not materialize total-sized lists. A later click observes later results.
- Preload successful/unexpired paths sequentially. Reuse current cache hits,
  skip failed/unfinished/expired/empty groups and continue after individual
  image errors. Page failures stop with partial-progress error; no automatic
  retry. Follow existing401/session cleanup.
- Explicit start expands this selection's cache to256 entries AND256MiB PNG
  Blob bytes until close. No new persistence/HTTP cache or server TTL extension.
  Background reads cannot evict earlier entries just to continue; stop with a
  capacity status. Foreground navigation may retain its normal bounded LRU/
  transient behavior under the expanded budget; pin the displayed URL.
- Count real currently retained URLs/bytes, checked groups/processed images,
  skipped groups and failed images separately. Historical image_count includes
  expired results and is not an available-image total. Capacity/error/cancel
  and per-image failures cannot be labelled as full successful completion.
- Preload has a selection/session epoch independent of per-navigation epochs.
  Arrows/refresh/current downloads remain usable without cancelling bulk work.
  Preloading never changes current job/image/index/filename/selection or draft,
  never stops/restarts/resubmits a server run. Foreground/background duplicate
  byte reads may overlap; recheck cache before URL creation and retain one URL.
  If expansion makes a displayed transient PNG cacheable, transfer that same
  URL into the cache using accepted metadata and the earlier original expiry.
- Cancel aborts background reads/scheduling and retains completed cache entries.
  Close/replacement/reset/logout-start/401/dispose invalidate late handlers,
  abort work, reset progress/default budgets and revoke all owned URLs. Late
  blobs cannot refill a closed/different selection. Background rejection on
  capacity must never allocate a transient display-owned URL.

### Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Explicit preload / repeated start | One pass; concurrent starts suppressed |
| Active experiment grows during pass | Finite initial bound; later click finds additions |
| Previously cached path | Reuse without another background PNG read |
| Failed/unfinished/expired/empty group | Skip with truthful group count |
| Individual image fails | Count failure and continue later images/groups |
| Metadata page fails | Partial error; explicit retry available |
| Count/byte budget exhausted | Capacity status; no preload eviction or false all-loaded claim |
| Navigate during bulk work | Independent current view and preload lifecycle |
| Cancel then restart | Retain cache; re-read metadata and reuse valid PNGs |
| Close/logout/401/different selection during read | Abort/invalidate; no stale URL/cache fill |

### Good / Base / Bad Cases

- Good: explicitly load a72-image experiment and compare its cached PNGs with
  arrows while preserving fresh metadata and any applicable numeric expiry.
- Base: ordinary single-image opening loads one selected PNG under32/64MiB budgets.
  Saved datasets initially open the thumbnail grid without a full PNG, under
  [Dataset Review and Cleanup](../backend/dataset-review-contract.md).
- Bad: download1000 images into32-entry LRU while claiming all are cached, or
  mark expired historical images as successfully available.

### Verification Required

Use ESLint/TypeScript, independent full affected-source review and fresh
explicit env-free build. No frontend/helper/browser automated tests or paid/
live/private-image probes. Review multipage/multi-image/growing runs, valid hits,
count+byte exhaustion, pinned/oversized URLs, image/page failures, cancel/restart,
navigation races and all protected session cleanup paths. Publish static web
only with unchanged API release/PID and retained old assets. Runtime interaction
remains operator acceptance.

### Wrong vs Correct

- Wrong: tie bulk cancellation to viewerEpoch, or call the foreground transient
  URL allocator after background cache admission fails.
- Correct: selection-owned epoch/controller, non-evicting background admission
  and a truthful capacity result while keeping ordinary navigation usable.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| A → B → A within budgets and expiry | Fresh metadata, reuse cached A URL |
| New image exceeds count/byte budget | Evict LRU entries and revoke their URLs |
| One image exceeds 64 MiB | Display transiently, release on navigation |
| Expired/missing image in current metadata | Placeholder/error; no stale cache hit |
| Failed/aborted image read | No cache entry or leaked URL |
| Close/reset/logout/401/dispose during read | Late result cannot refill the cache |
| Close then reopen same record | Authenticate/load again; prior URLs revoked |

## Good / Base / Bad Cases

- Good: compare two saved groups repeatedly; metadata stays live while the two
  PNG URLs are reused. Recently revisited images survive LRU eviction.
- Base: a one-image viewer owns one URL and releases it on close.
- Bad: using cached bytes without current metadata, persisting private images
  in browser storage, or revoking a displayed URL while retaining its reference.

## Verification Required

Respect the operator restriction: no frontend/helper automated tests or browser
automation. Run ESLint/TypeScript, independent source review and a fresh explicit
env-free locked build. Review same/multi-group revisit, LRU/count/byte bounds,
active URL safety, expiry, oversize/failure, overlapping navigation/close/session
races and existing ordinary-image ownership. Real interaction is operator
acceptance; do not issue paid requests for cache verification.

## Wrong vs Correct

- Wrong: switch away, revoke A, then refetch its bytes on every return.
- Correct: cache A within the open viewer, revalidate metadata on return and
  release its URL when its bounded cache ownership ends.

## Dataset grid review (2026-11-03)

- 「网格检查」 in the saved viewer of a dataset experiment (`ReviewGrid.tsx`,
  lazy chunk). Reads group metadata in 100-group pages (≤3000 groups), then
  shows 60 tiles per page; only the shown page fetches WebP previews
  (`WorkspaceApi.thumbnail`, 4 at a time, `thumbnail_busy` retried ≤3 times)
  and every preview Blob URL is revoked on page change/close. Previews never
  enter the full-PNG LRU; 「查看原图」 opens the normal viewer via
  `SavedResultsStore.showGroup(offset, image)`.
- The per-tile ⊘ / ↶ button toggles the discard mark (same PUT/DELETE as the
  viewer); clicking the image itself only selects it. Filters:
  item category (from the frozen item id prefix) and 「隐藏已弃置」.
- Saved datasets now select this grid on each explicit open, with hide-discarded
  initially enabled. Explicit current-set permanent cleanup, purged-slot omission,
  and affected preview/full-image URL invalidation follow
  [Dataset Review and Cleanup](../backend/dataset-review-contract.md).
- Key review instances by set ID plus the store's per-open `selectionVersion`,
  so reopening the same ID resets defaults and invalidates old async UI handlers.
- Keep that keyed `ReviewGrid` mounted throughout the dataset selection.
  `saved.grid` controls the detail dialog's visibility, not the grid's lifetime:
  opening/closing detail preserves page, filters, selection, editors, scroll and
  grid-owned preview URLs. Ordinary saved generations and style experiments
  retain inline detail. Explicit refresh, changed visible paths and full
  selection teardown still follow the existing invalidation rules.
- Render the existing dataset detail in a body-portaled native modal dialog.
  Close/X, Escape and backdrop call `saved.showGrid()`, not `saved.close()`;
  detail images/preload are released independently of grid previews. Guard
  cancel/backdrop handlers by `event.target === event.currentTarget`, including
  nested reference-preview portals. Restore connected opener focus with
  `preventScroll`, or focus the retained grid when the opener was removed.
- `SavedResultsStore.subscribeReviewChanges(listener): () => void` bridges
  accepted detail caption/discard/rerun mutations into the retained grid.
  Notifications check the captured selection object, independently of the
  current detail `viewerEpoch`: a successful write still updates its original
  grid after detail navigation/close, but never a replaced selection. Clear
  listeners on full close/reset and unsubscribe with the grid metadata effect.
- Apply caption/discard events as targeted job/slot field patches, preserving
  unrelated grid changes. Buffer events while initial metadata is pending so
  an older read cannot erase an accepted write. Merge accepted reruns with the
  initial queue snapshot by run ID, retaining the newer `updated_at` / cursor,
  before deriving pending source counts. Preserve accepted source replacement
  counts until explicit refresh for conservative quick-pick exclusion; the
  displayed pending count still follows the queue's `next_ordinal`.
  Keep the bound subscription identity stable; dialog visibility must not
  invalidate either metadata or thumbnail effects.
- Reject late rerun callbacks after selection replacement/full close/session
  teardown, including the grid's own accepted batch callback after unmount.
  Closing only the detail dialog retains selection ownership and still permits
  accepted queue updates.
- 「重跑全部待替换」: after one confirm showing the paid count, submits one
  rerun per discarded image and per failed group not yet replaced
  (`pendingReruns`: wanted − existing groups whose `rerun_of` names it),
  sequentially. Only `429 queue_full` is waited out and resubmitted (5 s,
  ≤120 waits); any other API error stops; a network error stops as
  "outcome unknown" and asks for a refresh before continuing. Stop cancels
  between submissions.

### Detail dialog validation

| Condition | Required behavior |
| --- | --- |
| Open/close detail on a filtered later page | Same grid instance, scroll, selection and preview URLs; no grid refetch |
| Accepted caption/discard after detail closes or changes job | Patch original job in the retained selection only |
| Accepted write races with initial metadata | Replay targeted patch over accepted metadata |
| Rerun acceptance overlaps initial queue read | Merge by run ID without double counting |
| Escape in nested reference preview | Close preview, preserve parent detail dialog |
| Full close/replacement/logout/401/dispose | Unmount grid, revoke owned URLs and reject late handlers |

Review these source paths with ESLint/TypeScript and a fresh env-free locked
production build. Continue the operator restriction on frontend/helper/browser
automated tests and real private dataset probes; interactive UI acceptance
belongs to the operator.
