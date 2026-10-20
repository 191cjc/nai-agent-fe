# Explicit Experiment Image Preloading (2026-10-20)

## Boundary

The operator requests a button to start loading all experiment-result images.
Existing SavedResultsStore owns authenticated lazy navigation and bounded PNG
URLs, while SavedResults.tsx owns the comparison viewer. Add explicit bulk read
state in that owner and a button/progress/cancel in the experiment viewer. Expected
product files: saved-results.ts, SavedResults.tsx, styles.css only. No new API,
backend/runtime/storage dependencies, generation behavior or paid work. Existing
follow-up/commit/web-publication authority applies; retain the running API.

This supersedes older spec bans on reading whole experiments ONLY for explicit
user-started preloading. Default viewing remains lazy and bounded32/64MiB.

## Behavior

Show 加载全部图片 for an open saved experiment (not ordinary saved generations).
Click starts a single background pass over that experiment's already recorded
groups. Read metadata in bounded pages (20 groups) through WorkspaceApi.experiment;
freeze the initial group-count bound so a growing server run cannot cause an
endless task. New groups/completions may be included by a later explicit click.
Do not materialize the whole run/plan or allocate total-sized arrays.

Only successful groups with unexpired image metadata have downloadable paths.
Reuse cached images; load missing images sequentially (one preload image read at
a time), retaining existing safe same-origin/authenticated image API. Failed,
empty and expired groups are skipped with truthful counts. An individual image
failure increments a failure count and continues; metadata/page failures are
visible and leave a retryable partial result. No automatic HTTP/provider retry.
401 follows existing session cleanup and invalidates all related state.

Progress distinguishes reading metadata, processed groups/images, currently
cached images, skipped/unavailable and failures, completion/cancel/capacity/error.
Do not present historical image_count (includes expired) as current available
images or claim completion while discovering pages/when capped. Repeating after
cancel/failure/completion checks metadata and reuses retained PNGs. Navigation,
refresh and downloads remain usable, and preloading never changes the displayed
selection/index/job/metadata or filename, draft or server experiment controls.

## Cache and lifecycle

Explicit preload opts this viewer into larger still-bounded session memory:
at most256 PNG URLs AND256MiB compressed Blob bytes, replacing the ordinary
32/64MiB budget for this selection until close. Use the existing cache/URL owner,
not a second whole-run cache. No persistent browser/HTTP cache, WebStorage,
IndexedDB or changed server expiry. Keep original expiry and require accepted
fresh metadata on navigation. No image decoding/prefetching of DOM elements.

Preloading must not evict its earlier loaded images merely to continue the
pass; stop with a truthful capacity status before count exhaustion or when a
new Blob will exceed byte capacity. Foreground display remains safe and usable
under the same enlarged budget, with existing LRU/transient-image behavior.
A background capacity rejection must not create a transient/display-owned URL.
Count currently retained images from real cache ownership (not only historical
successful reads), including eviction/expiry effects. Recheck cache before URL
creation after an overlapping foreground/background fetch; no duplicate URL
ownership or leaks. Two concurrent foreground/preload byte reads are acceptable;
keep foreground cancellation independent of background progress and vice versa.

A dedicated preload epoch/controller belongs to the open selection/session,
not the per-navigation viewerEpoch. Moving arrows or retrying group metadata
cannot cancel the bulk pass or accept stale foreground results. Cancel aborts
preload requests and stops new scheduling, retaining already cached images and
current navigation. Selection replacement/close/reset/logout-start/401/dispose
abort the pass, invalidate its completion/finally paths, clear all progress,
restore default cache budgets and revoke all owned URLs. Late blobs may not
refill a closed or different selection. Keep the displayed URL pinned against
background eviction; expiry invalidation remains authoritative.

## Validation / Release

Use Trellis implement agent then independent full affected-frontend checker;
ESLint/TypeScript/source review and a fresh locked env-free production build.
No frontend/helper/browser automated tests or live/private-result/paid-provider
probes. Backend unchanged, so do not rerun its full suite without a reason.
Source-review pages>1, multiple images/group, concurrent growing run, cache hits,
256/byte-cap boundaries, active pinned URL, per-image errors, expired/failed/
empty groups, cancel/restart, arrow/background races and close/session cleanup.

Publish static web assets only, verifying exact working/commit/build source
sets and hashes and retained previous assets/public readiness. Check live API
release/PID are unchanged; do not restart API or touch private state/images.
Interactive appearance/performance remains operator acceptance.
