# Full-height Prompt Drawer Quality Check

Independent full affected-frontend review: GREEN, no product corrections.
Only styles.css changed in the product; parent updated the requirement/spec.

- Expanded dock fills100% of its positioned canvas-stage. With border-box
  sizing and an opaque background it covers the entire underlying canvas.
- Mounted body's flex:1 1 0/min-height:0/overflow:auto fills the remainder
  below the toggle and scrolls internally. All former28dvh/300px/23dvh body
  limits are removed, including the short-screen override.
- Collapsed dock remains41px/35px. Absolute positioning and the constant
  reserved strip preserve canvas/image dimensions in either disclosure state.
- Generate, progress/reconnect/Stop, recovery/errors and left tools remain
  outside the overlay. Portal/native dialog, form/focus/history and saved
  viewer/cache/preload ownership remain intact across narrow/short layouts.
- Scoped build/publication helpers source-reviewed for exact source/hash
  checks, retained immutable assets, atomic switch/rollback and API guards.
- npm run lint (ESLint + TypeScript) and git diff --check passed. Fresh25-input
  isolated env-free locked build passed; no source changed after building.
- No frontend/helper/browser automated tests, helper execution by the checker,
  private-image/provider/paid probes or backend-suite reruns.

Actual visual interaction remains operator acceptance. The full-height rule
is captured in canvas-layout-contract.md and overlay-prompt-drawer-design.md,
superseding the first release's preserved small-sheet height.
