# Bounded In-Page Viewer Image Cache

## Trigger and Boundary

The operator observes repeated loading while switching historical comparison
images. Current image fetches use no-store, and SavedResultsStore releases its
single Blob URL on every navigation. Improve this existing comparison workflow
with a bounded viewer-owned memory cache of successful PNGs. This supersedes
the earlier selected-image-only ownership limit, without downloading whole runs.

Frontend implementer owns apps/web/src/saved-results.ts and only any necessary
adjacent browser changes. Parent owns artifacts/specs/build/commit/web release.
No API/storage/schema/auth-header/scheduler changes, HTTP disk caching,
IndexedDB/Web Storage, speculative prefetch or frontend/helper/browser tests.
No paid calls. Existing web publication authorization applies; API stays live.

## Contract

- Cache successfully fetched images by the exact validated authenticated image
  path, within the open viewer only. Hit reuses its Blob URL and refreshes LRU
  recency; no image-byte request. Continue fetching generation/group metadata
  normally, preserving live ordering, deletion/auth checks and expiration.
- Limit to 32 images AND 64 MiB of Blob.size. Evict least recently used entries
  and revoke their owned URLs. An oversized single image may be displayed
  transiently but must not become an over-budget cache entry. Keep the active
  display URL valid; count current cache entry toward limits, no second Blob.
- Respect original result_expires_at; expired entries cannot be reused and
  are pruned on access. Cache only successful PNGs, never errors/placeholders.
  API/image transport headers remain no-store. Cache hits still require the
  latest accepted owner-scoped metadata to expose that image path.
- Navigation releases the display reference, not a cached URL. Cache alone
  owns URL cleanup; revoke exactly when evicted, expired, closed/replaced,
  reset/logout/401/disposed. Uncached transient URLs retain display ownership.
  Existing epoch/AbortController guards prevent late reads from repopulating
  a closed/replaced/session-invalid viewer. Do not share ordinary result URLs.
- Opening another selection/close clears the cache; refresh/reload/logout
  cannot persist images or leak them to a later owner. Image filename/index,
  metadata, arrow boundaries and current download remain aligned.
- Revisit within bounds skips image download; beyond capacity, after expiry,
  or after closing/reloading requires authenticated loading again. No promise
  that decoded browser memory is exactly bounded by compressed PNG byte size.

## Verification and Release

Static source review: A->B->A same/multiple groups, LRU touch and size/count
eviction, active URL safety, oversize/error/expiry behavior, retry/navigation
races, close/reset/login/failed logout/401/disposal and metadata independence.
Run ESLint/TypeScript and independent trellis-check; no frontend/helper/browser
automated tests. Fresh env-free locked build with source/commit hashes, commit
and web-only release. Verify exact public HTML/assets/readiness/neighboring
health/retained old assets plus unchanged API pointer/PID/config/schema.
