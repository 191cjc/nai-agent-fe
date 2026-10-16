# Canvas and Bottom Prompt Dock

## Scope / Trigger

Use for App.tsx, SavedResults.tsx, StyleExperiment.tsx and styles.css layout
changes. The workspace centers one image canvas above a collapsible prompt
drawer and persistent bottom Generate controls. Left tool drawers are separate.
See workspace-contract.md for operations/auth and viewer-cache-contract.md for
saved image ownership; layout must preserve those contracts.

## Signatures

- Workspace owns local prompt disclosure state and explicit history navigation
  callbacks. GenerationStore remains the draft/operation/image owner.
- Result({ store, hidden }) remains mounted while the saved canvas is active.
- SavedResultViewer({ saved, onClose }) delegates returning to the current
  canvas and safe focus to Workspace; the store still owns URL cleanup.
- GenerateControls({ store, onOpenSettings }) renders a submit button with
  form="generation-form". That mounted form owns one generation.submit path
  even when its prompt inputs are inside the hidden drawer body.
- SavedResultsStore.selection determines saved versus current canvas visibility.
  Ordinary current-image selection uses already-loaded generation.images only.

## Contracts

- Use the remaining viewport height for the canvas. Prompt content scrolls in
  a bounded bottom drawer; Generate stays outside its collapsible body at the
  bottom. Main canvas, tool panel and prompt content own local scrolling.
- Render current generation or selected saved comparison as the main view,
  never stack two image sections. Closing saved viewing reveals current work;
  rendering/hiding alone must not clear stores, revoke URLs or trigger generation.
  Explicit saved close releases only its viewer ownership and preserves left
  tool disclosure. History resume separately dismisses its tool overlay; do not
  reuse that broader callback for the saved view's close button.
- Display one contained current image with thumbnail selection for multiple
  loaded images. Guard new job identity, empty/partial/short lists and correct
  current seed/index/filename/download. Local selection never fetches images.
  Preserve current pending/error/retry/parameters and explicit result cleanup.
- Saved comparisons keep lazy arrows, current metadata/weights/expiry, retry,
  download, viewer-local keys and bounded PNG cache. Image sizing adapts to
  available canvas space without cropping or a fixed height pushing controls
  offscreen. Empty and in-progress states still identify the canvas.
  Reserve actual image space after toolbar, caption and thumbnail chrome;
  metadata's auto-sized flex basis must not consume the entire canvas. Review
  combined progress + expanded prompts + metadata states at intermediate heights
  above the short-screen breakpoint, as well as very short/narrow viewports.
  Current CSS uses figure/metadata flex weights 3:1 with zero bases, bounded
  scrollable metadata, and a canvas minimum min(140px, calc(30dvh + 12px)).
  Keep the thumbnail strip in metadata, outside the figure's reserved image/
  caption space. Arrow height is capped at 100% of the available viewer height.
  At heights <=500px, expanded prompts retain a 47px dock minimum and nonempty
  operations retain 12px, leaving positive local scroll regions on short screens.
- Prompt drawer begins expanded and uses a native named disclosure button with
  aria-expanded/aria-controls. Keep editors/configuration mounted while hidden
  so tab/manual-edit/range state and characters survive. Hidden content cannot
  receive focus; explicit open/close paths transfer focus after rendering.
  The normal textarea blur-to-tags behavior still applies when using a toggle;
  do not suppress it or remount fields to implement disclosure.
- Preserve all style/shared/character/negative fields, positive target, exact
  weights and coordinate controls. Wide columns may stack on narrow screens.
  History reuse explicitly opens prompts and makes them reachable through the
  mobile overlay; history resume reveals current status with safe focus.
- Keep Generate's existing guards/labels/uncertainty and validation behavior,
  with one submit path and no nested forms. Explicit unlocked ordinary submit
  returns canvas selection to current work. Settings summary, unknown-submission
  actions and operation errors remain reachable while prompts are collapsed.
- Server experiment progress/reconnect/view/Stop stay outside the prompt body;
  closing it cannot detach/stop/restart server work. Bound verbose progress/
  snapshots so canvas and bottom actions remain reachable on short screens.
- Retain left rail order, mounted-hidden tool state, safe focus and narrow
  overlay behavior. Do not add global arrow handlers or paid action effects.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Toggle prompt drawer | Preserve content/configuration; no requests |
| Generate with drawer closed | Same guarded form submit, current canvas visible |
| Active/uncertain operation | Existing locks, recovery and Stop remain reachable |
| Select another ordinary image | Reuse existing URL; index/download stay aligned |
| New/partial/empty ordinary images | Valid current selection or status placeholder |
| Open/close saved comparison | Swap canvas view; independent owners remain valid |
| History reuse with collapsed prompts | Open prompts, dismiss overlay, safe focus |
| 320px width / short viewport | Local scrolling; reachable toggle and bottom action |

## Good / Base / Bad Cases

- Good: collapse prompts while comparing saved experiment images; the canvas
  grows and arrows reuse retained cached PNGs. Stop remains available separately.
- Base: empty workspace shows a canvas placeholder and the open prompt dock.
- Bad: unmounting prompt fields on collapse, placing Stop inside hidden content,
  or keeping a fixed 55vh image frame above an additional bottom editor.

## Verification Required

Run ESLint/TypeScript, source review of all affected frontend interfaces and a
fresh env-free locked build. Review new/partial/multiple results, download/index,
drawer disclosure/focus/form semantics, history reuse/resume, saved cache races,
all active/uncertain/failed/logout states and narrow/short scrolling. Respect
the operator restriction against frontend/helper/browser automated tests or
paid probes. Visual/desktop/mobile interaction remains operator acceptance.

## Wrong vs Correct

- Wrong: prompts occupy the first screen while generated images sit below them.
- Correct: the image canvas owns the main area, prompts occupy a bounded bottom
  disclosure, and Generate remains at the bottom in either disclosure state.
