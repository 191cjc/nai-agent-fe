# Canvas and Bottom Prompt Dock

## Scope / Trigger

Use for App.tsx, SavedResults.tsx, StyleExperiment.tsx and styles.css layout
changes. The workspace centers one image canvas with a collapsible prompt
overlay and persistent bottom Generate controls. Left tool drawers are separate.
See workspace-contract.md for operations/auth and viewer-cache-contract.md for
saved image ownership; layout must preserve those contracts.

## Signatures

- Workspace owns local prompt disclosure state and explicit history navigation
  callbacks. GenerationStore remains the draft/operation/image owner.
- Result({ store, hidden }) remains mounted while the saved canvas is active.
- SavedResultViewer delegates returning to the current canvas, safe focus and
  explicit seed-use actions to Workspace; the store still owns URL cleanup.
- GenerateControls({ store, onOpenSettings }) renders a submit button with
  form="generation-form". That mounted form owns one generation.submit path
  even when its prompt inputs are inside the hidden drawer body.
- SavedResultsStore.selection determines saved versus current canvas visibility.
  Ordinary current-image selection uses already-loaded generation.images only.
- Workspace's local canvas-stage contains the canvas-region and prompt-dock.
  The stage owns their positioning/stacking; operation/recovery/footer controls
  are normal-flow siblings outside this stage.
- canvas-stage defines --prompt-toggle-height (40px, or34px at heights<=500px)
  for both the toggle's fixed basis and constant bottom padding plus1px border.

## Contracts

- Use the remaining viewport height for the canvas stage. Reserve only a
  constant collapsed-toggle strip in both disclosure states. Anchor the dock
  absolutely to the stage bottom, with max-height:100% and local scrolling.
  When its mounted body is not hidden, the expanded dock fills100% of the
  stage and its body flexes into all remaining height below the toggle; no
  28dvh/300px or short-screen23dvh small-sheet height remains. It covers the
  entire image/main canvas from main-content top to persistent bottom controls,
  without resizing/recentering
  the canvas or image. Never allocate the expanded body in normal flow.
  Generate, operation progress/Stop and recovery/errors stay outside the
  overlay. Main canvas, tool panel and prompt content own local scrolling.
  Use local stacking below the narrow left scrim/panel/rail; preserve the
  body-portaled section assistant and native snapshot dialog. No viewport-fixed
  bottom offsets, JavaScript footer measurement or modal/backdrop is needed.
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
- Both current and saved image frames expose the actual accepted job seed
  at the lower right as an explicitly labelled button, with a visible Save
  button in the caption. Clicking the seed fills only the generation seed
  setting; an ordinary image/view change never pins a seed. Save exports a sanitized PNG under the
  workspace contract and retains selection/filename alignment on async changes.
  Keep the full seed and actions reachable at narrow widths and short heights.
- Saved comparisons keep lazy arrows, current metadata/weights/expiry, retry,
  download, viewer-local keys and bounded PNG cache. Image sizing adapts to
  available canvas space without cropping or a fixed height pushing controls
  offscreen. Empty and in-progress states still identify the canvas.
  Reserve actual image space after toolbar, caption and thumbnail chrome;
  metadata's auto-sized flex basis must not consume the entire canvas. Review
  combined progress + expanded prompts + metadata states at intermediate heights
  above the short-screen breakpoint, as well as very short/narrow viewports.
  Figure/metadata use flex weights 3:1 with zero bases and bounded scrollable
  metadata. A prompt disclosure change alone leaves their allocation unchanged.
  Keep the thumbnail strip in metadata, outside the figure's reserved image/
  caption space. Arrow height is capped at 100% of the available viewer height.
  On short screens, cap the dock to its stage, keep its toggle reachable and
  shrink/scroll its body. Do not reintroduce an expanded normal-flow dock
  minimum. Nonempty operations keep their independent bounded scroll region.
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
- Hidden shared/character prompt sections have a visibly distinct tinted card
  and editor background, a contrasting border/accent and a text/icon hidden
  status. Keep the restore action prominent. Section text and all local editing
  controls remain readable and usable; do not dim the whole card with opacity,
  disable its controls or confuse section visibility with individual tag comments.
- Keep Generate's existing guards/labels/uncertainty and validation behavior,
  with one submit path and no nested forms. Explicit unlocked ordinary submit
  returns canvas selection to current work and immediately collapses the prompt
  drawer. Move focus out of a hidden editor/assistant when necessary, without
  unmounting prompt state. Guarded/disabled submissions do not change disclosure.
  Settings summary, unknown-submission actions and operation errors remain
  reachable while prompts are collapsed.
- Server experiment progress/reconnect/view/Stop stay outside the prompt body;
  closing it cannot detach/stop/restart server work. Bound verbose progress/
  snapshots so canvas and bottom actions remain reachable on short screens.
- Retain left rail order, mounted-hidden tool state, safe focus and narrow
  overlay behavior. Do not add global arrow handlers or paid action effects.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Toggle prompt drawer | Same canvas/image size; overlay expands; preserve content/configuration; no requests |
| Generate with drawer closed | Same guarded form submit, current canvas visible |
| Generate with drawer open | Collapse immediately after guards; preserve editor state and safe focus |
| Active/uncertain operation | Existing locks, recovery and Stop remain reachable |
| Select another ordinary image | Reuse existing URL; index/download stay aligned |
| Click result seed / clear setting | Explicit seed-only draft update / blank random seed |
| Save / change image or session during export | Sanitized PNG only / suppress stale download |
| New/partial/empty ordinary images | Valid current selection or status placeholder |
| Open/close saved comparison | Swap canvas view; independent owners remain valid |
| History reuse with collapsed prompts | Open prompts, dismiss overlay, safe focus |
| Hide/show a prompt section | Distinct hidden card/editor/status and visible restore action; preserve editable text |
| 320px width / short viewport | Local scrolling; reachable toggle and bottom action |

## Good / Base / Bad Cases

- Good: expand prompts while comparing saved experiment images; prompts cover
  the entire unchanged canvas and arrows reuse retained cached PNGs. Stop remains
  available separately. Collapse reveals the same canvas at the same size.
- Base: empty workspace shows a canvas placeholder and the open prompt dock.
- Bad: unmounting prompt fields on collapse, placing Stop inside hidden content,
  shrinking the canvas in normal flow, or keeping a28dvh bottom sheet when the
  expanded drawer must cover the whole canvas.

## Verification Required

Run ESLint/TypeScript, source review of all affected frontend interfaces and a
fresh env-free locked build. Review new/partial/multiple results, download/index,
drawer overlay/unchanged canvas bounds, disclosure/focus/form semantics,
history reuse/resume, saved cache races,
all active/uncertain/failed/logout states and narrow/short scrolling. Respect
the operator restriction against frontend/helper/browser automated tests or
paid probes. Visual/desktop/mobile interaction remains operator acceptance.

## Wrong vs Correct

- Wrong: expanded prompt content takes height away from the image canvas.
- Correct: a local bottom-anchored prompt overlay occludes the unchanged canvas,
  while Generate and operation controls stay reachable below its stage.
