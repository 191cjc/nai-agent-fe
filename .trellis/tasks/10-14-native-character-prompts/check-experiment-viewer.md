# Independent Check: Experiment Image Navigation

Date: 2026-10-15

## Scope

Reviewed the current follow-up diff against HEAD in
`apps/web/src/StyleExperiment.tsx` and `apps/web/src/styles.css`, with the
Experiment Image Navigation requirements, implementation plan and updated
frontend style-experiment contract. Earlier native-character, prompt-weight,
sampler and submission-refusal implementations are outside this follow-up.
Read the unchanged archive, reset/auth and ordinary-result paths to establish
the new viewer's lifecycle and data ownership.

## Findings (fixed)

None. No source edits were necessary.

## Findings (not fixed)

None. No defects or unresolved product decisions were found in the reviewed
follow-up.

## Source Review Evidence

- `StyleExperimentResults` gives each archived row `max(1, images.length)`
  positions and resolves one selected row/image in archive order. Thus two
  images in group 1 precede group 2's empty placeholder, then group 3's
  images. A single-image archive disables both arrows. Navigation clamps at
  either end and never wraps. The displayed total is labeled `对比`; actual
  image count is separately labeled `张图像`, so placeholders are not counted
  as images.
- The viewer has one image element or one empty-group placeholder. Position,
  ordinal, returned-image index, job status, weights, request/effective seed,
  parameters, errors and the download URL/name all derive from the same
  resolved row/image. Failed rows retain their existing typed error and image
  warning. The seed label stays at request/group level; it does not invent
  individual sample seeds.
- Previous/next controls are explicit `type="button"` buttons with accessible
  names and disabled boundary states. Direction-key handling is attached
  only to the focusable viewer, whose descendants are arrow buttons, image
  or placeholder; it contains no editable controls. Prompt/settings inputs,
  download and parameter details are outside that key handler. Modified or
  already-handled key events are ignored. Movement focuses the viewer without
  scrolling, so reaching a disabled boundary does not strand keyboard focus.
- CSS uses a stable viewport-bounded frame height, `minmax(0, 1fr)` center
  column, fixed side arrows and `object-fit: contain`. The mobile override
  retains this same one-image structure with smaller columns. Intrinsic image
  dimensions cannot change the frame height or crop the image. Focus remains
  visible and captions/placeholder text may wrap.
- Store `finishOperation()` appends a settled row once and transfers its image
  array before clearing active images. Archived arrays are not subsequently
  extended or replaced; `refresh()` ignores archived jobs. Appending a row
  keeps the experiment object's identity, so the local position remains on
  the same image. No full Cartesian product or expanded image list is
  allocated by the viewer.
- The position resets when the experiment reference changes. A valid new
  Start creates a new empty run only after preflight, while explicit clear,
  logout/suspension and protected reset clear the archive. Invalid Start and
  ordinary generation preserve it. App logout also unmounts the workspace.
  Existing disposal releases archive URLs through the store.
- Movement only updates local React state and focus. It does not submit,
  poll, fetch, retry, change a draft or revoke object URLs. Existing clearing
  guards are preserved. No store, API, scheduler, provider, dependency or
  ordinary result changes occur in the current source diff. New CSS selectors
  are experiment-scoped; ordinary `.image-grid` and `.image-item` remain
  unchanged. Removed grid/pagination rules have no remaining experiment users.
- The updated frontend contract and task design describe the implemented
  single-image navigation and retain archive/URL ownership in GenerationStore.

## Verification

- Lint: PASS — `npm run lint` from `apps/web`; ESLint completed successfully.
- TypeCheck: PASS — the same command completed `tsc --noEmit` successfully.
- Whitespace: PASS — `git diff --check` returned no findings.
- Tests: not run, as required by the retained restriction on frontend/helper
  automated tests and browser automation. No paid/provider calls were made.
- Production build/publication is owned and verified separately by the main
  session. This review makes no runtime/browser or real-provider claim.

Reviewed source SHA-256:

```text
0447e60590b85d42ecf3478f88abf03abb331368345fef686668284241cfbe8d  apps/web/src/StyleExperiment.tsx
199736fdefd50466d52b98cc62233c4516e0885992b7c22dd9770080806e9204  apps/web/src/styles.css
```

Operator desktop/mobile, mouse/keyboard and actual-image acceptance remain
pending. These limitations do not indicate a source/static-check failure.
