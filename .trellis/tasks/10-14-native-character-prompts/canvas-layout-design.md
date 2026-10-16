# Canvas-Centered Workspace Layout

## Outcome and Change Boundary

The operator requests NovelAI's canvas-centered composition: the main body is
an image canvas, prompt inputs live in a collapsible bottom drawer, and Generate
is at the very bottom. The current App.tsx stacks editor, saved viewer and result
in one main-scroll; styles.css gives the editor unbounded height. Reorganize
these owning UI components, keeping store/API/cache/job behavior intact.

Implementation ownership: App.tsx and styles.css; SavedResults.tsx and
StyleExperiment.tsx only for necessary visual integration. Parent owns docs,
specs, build, commits and web-only release. No store/API/schema/dependency,
credential, provider, image-cache or generation-scheduling changes. No frontend/
helper/browser automated tests or paid calls. Existing web publication authority
continues; API/background experiments remain live.

## Layout and Interaction Contract

- Keep the header and left settings/history/tags/advice rail/drawers. The main
  column is a full-height flex/grid composition, with a dominant canvas above
  a bottom prompt dock and a persistent bottom Generate action bar. Avoid
  whole-document/editor-before-result scrolling.
- The canvas shows current generation OR the explicitly selected saved result,
  never two full result sections stacked. Preserve saved-result left/right
  navigation, metadata/weights/expiry, refresh and current download. Closing the
  saved view returns to current generation and preserves left tool disclosure;
  history resume separately closes its overlay. Existing URL owners stay in stores;
  changing visibility must not clear saved PNG cache or ordinary result URLs.
- Current generation displays one contained active image, with local previous/
  next controls and a compact thumbnail strip for multiple already-loaded
  images. Keep the correct index, seed, current filename/download, parameters,
  pending/error/retry states and terminal cleanup. No fetch/prefetch on local
  ordinary-image selection. New job identity resets selection safely; partial
  image arrivals and short/empty lists cannot select an undefined image.
- Empty/pending/failed/experiment-running states still provide a clear canvas.
  Images fit available canvas space without cropping; large metadata/details
  can scroll locally. Do not reserve a large static image height that pushes
  the prompt toggle or Generate outside the viewport.
- Prompt drawer starts expanded. A named native disclosure button with
  aria-expanded/aria-controls toggles its bounded independently scrollable body.
  Collapsing does not unmount prompt editors/configuration or reset text, tag
  view/manual edit state, selected positive target, characters/positions, side
  positive/negative tab, or experiment range selection. Hidden content cannot
  receive keyboard focus. Focus must not remain inside a newly hidden region.
  Existing textarea blur-to-tags still applies when clicking the toggle;
  preserving mounted state does not suppress the normal blur transition.
- All existing style/shared/characters/negative editors live inside that drawer.
  Preserve blur-to-tags/manual edit and weight semantics. Layout can use columns
  at wide widths and stack at narrow widths; do not change draft/request fields.
- A form-associated Generate button remains at the very bottom when drawer is
  open or closed. One user submission uses existing generation.submit and the
  exact operation/uncertainty/active-run guards, labels and errors. Explicit
  unlocked ordinary submit returns canvas selection to current generation;
  visibility changes never submit. Avoid nested forms or implicit extra POSTs.
- Settings summary/button remains reachable next to the bottom action. Unknown
  submission controls remain outside the collapsible body, with original
  check-history/acknowledge behavior. Keep failure/errors visible on canvas or
  action area even while prompts are collapsed.
- Experiment progress/reconnect/view saved/Stop are outside the prompt body,
  compact and bounded, so collapsing never hides operation controls. Frozen
  configuration/details retain existing state and behavior.
- Replace history reuse's old scrollIntoView-only action with an explicit
  open-prompt action and safe focus after render; preserve reuse mapping and
  close the mobile left overlay so editing is reachable. History resume returns
  the canvas to current generation and safely reveals/focuses status. Existing
  tag insertion still changes only its chosen target, without submitting.
- Desktop, 320px-wide mobile and short landscape viewports retain reachable
  prompt toggle and bottom Generate; drawer/tool/canvas regions own scrolling.
  Keep keyboard navigation local to image viewers; do not capture editing keys
  globally. Native buttons work with Tab/Enter/Space and visible focus.

## Verification and Release

Implementer runs npm run lint (ESLint + TypeScript), diff check and source
lifecycle review; freeze before independent trellis-check. Check full affected
frontend UI/store/API interfaces, disclosure/focus/form submission, active-run/
uncertain/failed/logout state, cached saved comparison and local current-image
selection across empty/new/partial/multiple results. No frontend/helper/browser
automated tests; no backend repeat is needed for unchanged backend.

Parent synchronizes frontend layout spec, builds fresh env-free locked explicit
web inputs, commits and publishes only the web. Review build/release scripts,
verify exact public assets/health/old assets and unchanged API pointer/PID.
Record release/journal; broader real-provider/interactive acceptance stays open.
