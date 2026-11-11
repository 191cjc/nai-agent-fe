# Training-set thumbnail defaults and discarded-image cleanup

## Goal

Default training-set review to thumbnails with discarded images hidden and add confirmed permanent cleanup of discarded images without inspecting private datasets.

## Background

- The operator confirmed cleanup is limited to the currently opened training set (2026-11-07).
- Saved training sets currently open in the single-image viewer: `apps/web/src/SavedResults.tsx:250` and `apps/web/src/saved-results.ts:149`.
- The thumbnail grid already has a hide-discarded checkbox, initially false: `apps/web/src/ReviewGrid.tsx:150`.
- Discard/restore currently changes a reversible per-image marker and preserves files: `apps/api/src/novelai_api/app.py:947` and `.trellis/spec/backend/dataset-run-contract.md:91`.

## Requirements

- R1: Opening a saved training set initially shows its thumbnail review grid.
- R2: Thumbnail review initially enables the existing hide-discarded filter.
- R3: Provide a button in thumbnail review to permanently remove every discarded image in the currently opened training set, including its re-run images. The operation covers all pages/categories/search results, independently of the current selection/filter. Confirmation identifies the current set and states that deletion is irreversible.
- R4: Preserve retained sibling images, image identities, training-set/group parameter history, existing generation behavior, and owner isolation. Cleanup must not initiate generation or advice. Permanently deleted images cannot be restored through the discard toggle or served by stale previews.
- R5: Never inspect training images, thumbnails, reference images, captions, dataset prompt text, exported datasets, production SQLite content, or private image storage. Inspect source/specs and permitted metadata only; validate using synthetic fixtures and mocks.
- R6: Report deleted, already unavailable, and failed cleanup counts truthfully. Permit explicit retry after partial failure. Refresh affected review/list metadata and release affected browser image URLs.

## Acceptance Criteria

- [x] Clicking a saved training-set cover or browse action opens thumbnail review without eagerly downloading a full-size PNG; switching to single-image review remains available.
- [x] Discarded images are hidden initially; the operator can still toggle the filter.
- [x] Canceling cleanup changes nothing; confirming removes discarded image bytes permanently across the current set, including hidden pages and re-runs.
- [x] Retained sibling images and foreign-owner data survive cleanup.
- [x] Current-set parameters/history, reference images, and snapshots survive cleanup. Remaining image URLs/indexes keep their original identity.
- [x] Deleted images are absent from review/export and cannot be restored or fetched as originals/thumbnails after restart.
- [x] The UI refreshes to reflect cleanup and reports success or failure truthfully.
- [x] Repeated cleanup is safe; already expired/missing images and partial filesystem errors do not cause false success or deletion of retained siblings.
- [x] Offline synthetic regressions, applicable API/schema checks, and the frontend build pass.

## Out of Scope

- Reading or modifying real operator datasets during development.
- Paid generation/advice calls, production deployment, or executing cleanup against real data as part of development.
- Cleaning other training sets, general history deletion, backup erasure, and changes to existing image-retention policy.
