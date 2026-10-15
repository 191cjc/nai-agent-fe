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

- Cache successful PNG Blob URLs only: at most 32 entries AND 64 MiB summed
  Blob.size. A hit refreshes LRU recency and avoids another image-byte request.
  These are compressed image bytes, not a bound on browser decoded memory.
- Continue normal group/generation metadata reads on navigation. A cache hit
  requires current accepted metadata exposing the same image path and a valid
  original result_expires_at. Do not cache metadata or extend server expiry.
- Prune expired entries on access. Evict least recently used entries until
  both budgets fit. Keep the displayed URL valid and include it in the budget;
  do not create a second Blob URL for a hit. A single oversized image can be
  displayed transiently but must not become an over-budget cache entry.
- The cache owns its URLs. Navigation releases the display reference; eviction,
  expiry or clearing revokes the cached URL. An uncached oversized image is
  display-owned and revoked when released. Failed loads/placeholders never
  enter the cache. Never prefetch neighbors or accumulate whole experiment runs.
- Close, opening another selection, reset, logout start, 401 and dispose clear
  the cache and revoke its URLs. A refresh has no persistent cache to restore.
  Epoch/abort/session guards reject late reads before URL creation/cache fill.
- Keep image, index, metadata, filename and current download aligned. Viewing
  and cache cleanup never mutate the draft or stop/resubmit paid server work.

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
