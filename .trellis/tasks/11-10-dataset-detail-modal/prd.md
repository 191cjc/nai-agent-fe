# Dataset task detail dialog

## Goal

Open a task selected from the saved training-set thumbnail grid in a dialog,
so closing its detail returns immediately to the same loaded grid. The operator
explicitly requests implementing this interaction in the current repository.

## Confirmed facts

`SavedResults.tsx` conditionally renders ReviewGrid or single-image detail.
`SavedResultsStore.showGroup()` sets grid=false, unmounting ReviewGrid and
revoking its page previews; returning remounts and fetches metadata/thumbnails.
ReviewGrid owns page, filters, multiselection, editors, scrolling and previews.
Existing native modal dialogs already provide focus restoration and Escape.

## Requirements

- R1: Dataset task/image detail opens in a responsive modal above the existing
  grid. Retain the current detail actions, navigation, parameters and editors.
- R2: Keep the same keyed ReviewGrid instance and its previews, page, search,
  category, hide-discarded, selected tiles and scroll during detail open/close.
  Read-only close must not refetch the grid metadata or thumbnails.
- R3: Close button, Escape and backdrop return to the grid and restore usable
  focus without closing the whole saved selection. Background remains inert.
- R4: Actual detail edits/discards/re-run queue changes must appear in the
  retained grid with targeted metadata reconciliation, not a blanket reload.
  Preserve purge/discard guards, expiry, bounded caches and race protection.
- R5: Selection replacement, full close, logout/401 and disposal still release
  owned resources and reject late responses. Ordinary generation and non-dataset
  experiment viewing keep their existing behavior.

## Acceptance criteria

- AC1 (R1-R3): Open a tile on a filtered later grid page, inspect/navigate detail,
  close it, and retain the grid instance/URLs/page/filter/selection/scroll.
- AC2 (R4-R5): Changed caption/discard/queue metadata is reconciled for matching
  jobs only; closing during reads cannot reopen the dialog or refill images.
- AC3: Existing ESLint/TypeScript and fresh env-free production build pass;
  independent source review covers modal, request/URL ownership and cleanup.

## Scope

Frontend-only scoped change. No backend, API, paid generation behavior, new
cache framework, persistent image storage, production deployment, training
pipeline changes or unrelated edits. No frontend/browser/helper automated tests
or live/private dataset/image/prompt/caption inspection. Preserve preexisting
README, journal, training task and backend-spec working changes.

## Frontend publication authorization

The operator subsequently explicitly requested immediate frontend-only
publication. This extends the initial no-deployment scope only to the reviewed
static web bundle. Do not publish/restart the API, change backend code/config,
run migrations, alter active runs, or change Nginx. Preserve previous web assets
and release, and verify the API release pointer and process remain unchanged.
