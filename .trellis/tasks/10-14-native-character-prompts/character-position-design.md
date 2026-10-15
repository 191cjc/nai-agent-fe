# Draggable Character Positions

## Boundary

Current browser/API character children contain prompt only, while the adapter
hardcodes x=y=0.5. Add manual coordinates to those owning representations,
pass them to the provider, and expose a bounded draggable preview. Do not add
automatic placement, pose/skeleton controls, disabled tags, clothing categories,
per-character negative prompts or reference images.

Backend owner: generations.py, mcp_images.py, affected offline tests and the
reviewed contracts/openapi.json. Frontend owner: api.ts, store.ts, App.tsx,
new CharacterPositions.tsx and its scoped styles.css rules. Parent owns all
task/spec artifacts, integration, release staging and publication.

## Cross-layer Contract

- CharacterPrompt adds x: float = 0.5, y: float = 0.5, both finite and within
  [0.1, 0.9]. Reject explicit null and out-of-range/non-finite values. These
  are the verified wrapper bounds in research/native-provider-contract.md;
  do not substitute a 0..1 provider contract. Coordinate omission stays valid.
- Browser CharacterPrompt exposes optional x/y to represent additive inputs
  and legacy data. CharacterDraft always owns numeric x/y plus its stable id.
  Serialize explicit validated coordinates for every nonblank character.
- Backend model defaults upgrade old saved JSON on read. Existing settings_json
  saves complete validated inputs without a migration. Adapter forwards each
  child's x/y with prompt, empty negative_prompt and enabled=true in order.
  No change to the 11-argument flat payload or capability check.
- New draft cards are centered. Reuse defaults missing x/y to 0.5, preserves
  explicit values and creates fresh stable IDs. Position updates increment
  draftVersion so pending latest-history initialization cannot overwrite them.
- Experiments capture coordinates immutably at Start; every combination uses
  that snapshot even if markers move later. Preserve coordinates through the
  requestFromDraft per-step validation reconstruction.

## Interaction

The board has the generation canvas aspect ratio (safe fallback for temporarily
invalid dimensions) and a bounded responsive size. Coordinates are normalized
to the full board: x increases rightwards and y downwards. Use two decimals
and 0.01 increments for keyboard adjustment (larger modified increments are
optional). Board edges do not permit values outside 0.1..0.9.

Markers follow stable character IDs, never surviving sibling indices. Keep
numbering matched to card order. Provide explicit selection for overlapping
markers, make the selected one reachable and visible, and distinguish blank
draft cards without making them submitted characters. Dragging touches draft
state only; it never submits, focuses a prompt or scrolls the page. Use pointer
capture, ignore unrelated pointers/buttons and cleanly end on up/cancel/lost
capture. Removing/reusing characters during a drag must not update another
character. Scope keyboard shortcuts to marker/control focus and preserve
visible focus and ordinary Tab navigation. No global listeners or browser
persistence. Keep pointer scrolling available outside the interaction control.

Show a concise placement-guidance hint, current selected coordinates and a
center reset. Put the control in the character section; existing prompt tags,
side drawers, experiment viewer and generation settings remain intact. History
and result parameter summaries should expose saved positions so reuse can be
understood. No frontend/helper tests or browser automation.

## Rollout / Verification

Run backend fake-provider persistence/default/boundary/adapter regressions,
full offline pytest, Ruff, frozen/lock checks and reviewed OpenAPI. Frontend
ESLint/TypeScript and source review cover pointer/keyboard bounds, overlap,
stable IDs, resize/aspect, reuse/legacy/reset/logout, initial-restore revision
and experiment snapshots. Build fresh explicit inputs without env files.

Stage a matched API/web release, verify source/commit hashes and a private
online DB backup, check active job counts without printing prompts/sessions,
then activate API and readiness before web. No configuration/credential edits
or paid probes. Existing authorization covers feature publication; keep old
assets/releases and retain the dedicated submission-refusal backend fix.
Prefer retaining the new API when rolling back web: the old adapter hardcodes
center and would ignore coordinates from already-open new pages. No DB restore
is needed for this additive change. API restart clears transient images.
