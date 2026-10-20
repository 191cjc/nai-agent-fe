# Overlay Prompt Drawer (2026-10-20)

## Boundary

The operator requires the bottom prompt drawer to cover the main canvas when
expanded instead of reducing its size. The current Workspace flex column puts
the full prompt-dock height in normal flow. Fix that layout owner directly;
expected product files are App.tsx (a local canvas/dock containing region) and
styles.css (positioning, bounds and responsive rules).

This follows the existing in_progress task and implementation/publication
authority. No new task or confirmation is needed. Preserve provider/API/stores,
prompt semantics and viewer URL ownership. No new dependencies, settings,
animations, backdrop/modal behavior or pointer/focus interception are needed.

## Behavior / Layout

- Use a positioned local stage for the current/saved canvas and prompt dock.
  Anchor the dock to the stage bottom. Its expanded content is out of normal
  flow, overlays/occludes the lower canvas, and cannot resize/recenter the
  underlying image. Reserve at most a constant collapsed-toggle strip in
  both disclosure states; canvas sizing must be identical for either state.
- Keep the stage inside the main column beside the desktop tool drawer,
  bounded to its actual available width/height. Do not use viewport-fixed
  offsets or JavaScript measurement of bottom controls. Native flex layout
  should account for existing dynamic progress/errors/uncertain bars/footer.
- Keep Generate, uncertain-result recovery, errors and experiment progress/
  reconnect/view/Stop outside the overlay, reachable and locally scrollable.
  Left tool overlays/backdrop/rail and app header remain above/outside this
  main-content drawer. Preserve section-helper/snapshot overlay ownership.
- Preserve the existing bounded prompt-body height where practical, capped
  to the stage on small/short screens, with an always-reachable named toggle
  and independently scrolling editor. Expanded drawer may cover canvas
  content; covered content is intentionally occluded, not resized to fit.
- Keep disclosure state/default-expanded, aria-expanded/aria-controls,
  mounted-hidden editors, focus handoff, blur-to-tags, helper cleanup,
  history reuse/open, resume and single external form submission unchanged.
  Opening/closing alone must neither fetch images nor change selections,
  drafts, cache ownership or server operations.

This supersedes earlier canvas-layout language claiming the canvas grows on
prompt collapse or giving an expanded dock a normal-flow minimum height.

## Validation / Release

Native implementer then independent full affected-frontend checker. Run
ESLint/TypeScript, git diff --check and a fresh25-input isolated env-free locked
production build. No frontend/helper/browser automated tests, live/private
result downloads, paid provider/AI requests or backend suite reruns.

Source-review current/saved/empty canvas, expanded/collapsed fixed canvas
allocation, narrow320px and short/intermediate viewport constraints, active
progress/uncertain/errors/footer, left overlays, prompt helper/modal stacking,
mounted form/editor and focus paths. Interactive visual acceptance remains
with the operator. Publish web-only using exact source/assets hashes and
unchanged API release/PID checks; do not restart API or mutate private state.
