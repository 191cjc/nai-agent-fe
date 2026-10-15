# Check: Draggable Character Positions

Date: 2026-10-15. Independent `trellis-check` review covered the full follow-up
in both discovered packages (`apps/api` and `apps/web`), their spec indexes,
quality contracts, PRD/design/plan and character-position-design.md. Parent
also reviewed the final cross-layer diff. No source defects or fixes.

## Data Flow Review

- Browser API permits legacy omitted axes. Every draft child owns stable id,
  numeric x/y and prompt. New/old cards center at 0.5. Only nonblank characters
  serialize prompt/x/y; client IDs never reach the API. Validation rejects
  invalid positions before POST and keeps native model/count/prompt guards.
- Backend axes independently default to 0.5; strict finite numbers must fall
  within inclusive 0.1–0.9. Null, booleans, strings, nonfinite or out-of-range
  values return the safe 422 before any job/provider work. OpenAPI adds only
  optional/defaulted bounded number x/y.
- Existing settings_json stores the complete request without a schema change.
  Ordered noncenter coordinates survive history, restart, backup/restore and
  reuse; pre-position native JSON supplies centered defaults. Owner isolation
  and legacy flat requests retain their behavior.
- MCP receives exact ordered child coordinates alongside prompt, empty child
  negative and enabled=true. Flat eleven-argument payload and conservative
  native capability checks stay intact; no paid retries are introduced.
- Reuse creates fresh client IDs and retains explicit positions; coordinate
  updates increment draftVersion to invalidate late entry restoration.
  Protected reset/logout clears drafts through existing lifecycle ownership.
- Experiment Start captures all character values; per-step requestFromDraft
  reconstruction preserves x/y. Subsequent draft dragging cannot change that
  snapshot. Prompt tag editing, seed locking, scheduler and image URL ownership
  retain their existing paths. Shared result/history summaries show positions.

## Interaction Source Review

- Board uses valid generation aspect ratio with a safe fallback and responsive
  size limits. Marker placement and pointer math share full-board normalized
  coordinates, x right/y down, clamped to 0.1–0.9 and rounded to two decimals.
- Primary left-button/touch pointer capture follows one stable ID, retaining
  the initial grab offset. Other pointers/buttons cannot take over. Up,
  cancel, lost capture, unmount and character removal/reuse end the drag;
  stale events cannot update a sibling.
- All cards have numbered markers and explicit selection buttons, so centered
  overlaps remain reachable. Selected/focused markers rise above peers.
  Empty cards are dashed/labeled and remain excluded from submitted children.
- Marker-focused arrows adjust 0.01, with scoped event prevention and ordinary
  Tab navigation/visible focus. Center reset is explicit. Pointer touch-action
  is restricted to markers; surrounding content remains scrollable. No drag
  submits generation or enters prompt editing.
- Existing latest-history guards, mounted left drawers, prompt tag/weight
  editor, ordinary results and experiment viewer were included in source
  review; no ownership or request side effects were introduced.

## Executed Verification

- Frozen offline dependency sync with test/lint extras: pass.
- Full offline pytest: **249 passed**, two existing dependency deprecations.
- Ruff `src tests`: pass. `uv lock --check --offline`: pass.
- Web `npm run lint` (ESLint and `tsc --noEmit`): pass.
- Deterministic OpenAPI snapshot regression: pass; no database creation.
- Task context validation: pass, 19 implement and 19 check entries.
- `git diff --check`: pass.

All backend checks used fake providers/transports with provider credentials
unset. No frontend/helper automated tests, browser automation or paid calls.
Static review is not operator desktop/mobile or real-provider acceptance.
Fresh env-free build and matched API-first deployment have separate records.
