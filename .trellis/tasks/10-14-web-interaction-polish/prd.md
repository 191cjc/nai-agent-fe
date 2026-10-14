# Fix workspace tab navigation and generation history refresh

## Goal

Make the workspace tools predictable to keyboard users and keep generation
history current when the generation being observed finishes.

## Background

- The user approved planning this two-fix frontend follow-up on 2026-10-14.
- `apps/web/src/App.tsx:304` handles keys using tags/advice/history, while
  `apps/web/src/App.tsx:347` renders history/tags/advice. Selection and DOM
  focus can therefore disagree, and Home/End do not follow the visual order.
- `apps/web/src/store.ts:201` notifies history after submission, but terminal
  status handling at `apps/web/src/store.ts:224` sends no history notification.
  The current wiring at `apps/web/src/store.ts:495` consequently leaves saved
  status stale until another history request.
- This is a lightweight follow-up to `09-23-novelai-web`. Requirements and
  acceptance live here; source findings and implementation considerations
  live in `research/interaction-findings.md`.

## Requirements

- **R1 — Keyboard order:** ArrowRight/ArrowLeft move selection and focus
  together through the displayed history/tags/advice order, with wraparound.
  Home selects and focuses history; End selects and focuses advice. Mouse
  selection and the existing drawer behavior remain available.
- **R2 — Terminal history synchronization:** On first observing a tracked
  generation as succeeded or failed, refresh parameter history, including
  when observation resumed from an existing history record. Refresh must not
  depend on whether images are present or their downloads succeed. Rechecking
  the same unchanged terminal result must not repeatedly refresh history.
- **R3 — Async consistency:** A terminal-triggered refresh preserves the
  user's history page and does not cancel a requested page change in favor
  of an older page. An in-flight history response must not permanently hide
  a newly observed terminal status. Refresh failures belong to history's
  error state and must not change a completed generation into a failed or
  uncertain submission. Logout/session expiry must invalidate stale work.
- **R4 — Existing boundaries:** Keep the typed same-origin browser API,
  parameter-only history, temporary image cleanup, draft preservation and
  protection against repeated uncertain paid submissions. Make no provider
  calls during validation.

## Acceptance Criteria

- [x] **AC1 / R1:** Walking all three tabs with each arrow key, including
  wraparound, keeps the active panel, selected tab and focused tab aligned.
  Home/End reach the first/last displayed tabs respectively.
- [x] **AC2 / R2:** First-observed success and failure each cause history to
  synchronize. This also works for a resumed job, expired/missing images and
  an image download failure.
- [x] **AC3 / R2:** Repeated manual status checks of the same terminal job
  do not cause additional completion-triggered history refreshes.
- [x] **AC4 / R3:** Completion during history loading or pagination eventually
  refreshes the intended page without an old in-flight response restoring
  a stale terminal status. History request failure preserves the generation
  result; stale post-logout responses cannot repopulate protected state.
- [x] **AC5 / R4:** Source review confirms unchanged generation POST behavior,
  API paths, credentials/storage boundaries and image cleanup. Frontend lint,
  TypeScript checking and an environment-free production build pass.
- [x] **AC6 / R1-R4:** Implementation and independent review record actual
  checks and any runtime-validation limits. No frontend automated/browser
  tests are added or run under the existing operator restriction.

Acceptance evidence is recorded in `verification.md`. AC1-AC4 are accepted at
the source-review boundary; the checked boxes do not claim browser execution.

## Out of Scope

- Backend routes, OpenAPI, SQLite migrations and provider adapters.
- New product features, visual redesign or frontend testing dependencies.
- Paid provider probes, deployment, production credentials and branch merging.

## Deferred Validation

The existing frontend task excludes automated/browser tests. Lint, type
checking, a clean build and source review can verify this patch's static
properties; desktop/mobile browser acceptance remains an operator follow-up.
