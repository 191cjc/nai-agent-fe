# Experiment Image Preload Quality Check

Independent native Trellis checker: GREEN; no product corrections required.
Affected product scope: saved-results.ts, SavedResults.tsx and styles.css only.

## Verification

- npm run lint: ESLint and tsc --noEmit passed.
- git diff --check passed.
- Fresh isolated locked production build passed with all25 web inputs;
  see preload-images-build-verification.md. Checker made no source changes.
- Full affected-frontend source review used current task artifacts and frontend
  cache, experiment, canvas and workspace contracts. Backend is unchanged.
- No frontend/helper/browser automated tests, private image downloads,
  authenticated session/provider/paid requests or backend test reruns.

## Reviewed Boundaries

- Explicit experiment-only action; ordinary saved generations remain lazy.
- Metadata pages of20 with the first group_count frozen; multiple pages,
  multiple images/group, empty runs and growing active experiments stay bounded.
- Cached PNG reuse, skipped failed/unfinished/expired/empty groups, individual
  image errors that continue, and page errors that end a partial pass.
- Default32/64MiB budget and explicit256/256MiB budget; background admission
  never evicts earlier entries or allocates transient URLs on capacity failure.
- Current cache count/bytes, processed groups/images, skipped groups, image
  failures and neutral completion/cancel/capacity/error labels stay distinct.
- Displayed URL remains pinned; an expanded-budget transient PNG transfers
  its existing URL; foreground/background overlap rechecks cache ownership.
- Independent navigation/preload epochs and controllers, cancellation/restart,
  stale finally handlers, close/replacement/reset/logout-start/401/dispose.
- Arrow navigation, refresh and downloads retain current-view ownership;
  bulk loading never changes drafts or server experiment execution.
- Narrow/short-screen toolbar and scrollable progress reviewed by source;
  actual interactive appearance/performance remains operator acceptance.
- Clean-build and web-only publication helpers reviewed by source only;
  exact source/asset guards, retained assets, atomic switch/rollback and
  unchanged API release/PID gates have no blocking findings.

## Spec Sync

viewer-cache-contract.md now defines the explicit bulk-load exception, actions,
budgets, progress, cancellation and URL ownership. style-experiment-contract.md
links the exception while preserving ordinary lazy viewing.
