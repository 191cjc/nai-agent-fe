# Native Character Prompt Editor

## Goal

Let users compose style, shared scene content and multiple independent
characters in the workspace, with the negative prompt behind a compact side
tab rather than consuming the positive editor's horizontal space.

## Confirmed Requirements

- The operator requested positive sections labeled `画风`, `公共` and `人物`,
  with multiple addable characters, and a special side tab for the negative
  prompt.
- After the compatibility distinction was explained, the operator explicitly
  chose native independent character control, including the required
  generation-service extension. Flattening character descriptions into one
  positive string does not satisfy this requirement.
- Existing requests, API models and the MCP adapter carry one positive string.
  Parameter history stores the complete validated request in `settings_json`;
  existing history and its reuse must remain compatible.
- Existing provider credentials remain private. No paid provider calls,
  browser automation or frontend automated tests are authorized for checks.

## Scope

- Separate style and shared positive editors, multiple independently editable
  character entries, add/remove controls, and a compact negative side tab.
- Typed browser/API representation and provider mapping that preserves native
  character boundaries. Preserve section content and character order in saved
  parameter history and on reuse.
- Keep old flat-prompt history reusable without inventing character boundaries.
- Make tag insertion explicit and direct it to the intended prompt section.
- Validate limits before submission and reject unsupported native provider
  capabilities clearly rather than silently combining or dropping characters.
- Verify through static frontend checks, clean production builds, offline
  backend regressions and independent source review.

## Out of Scope

- Paid image/advice probes or credential changes.
- Image uploads, references, Vibe transfer and manual character-position
  controls. Characters use the service's default centered coordinates; the
  inspected provider does not offer automatic positioning through this tool.
- Changes to advice inputs, authentication or historical image retention.

Exception authorized on 2026-10-15: after the matched release and concrete
enablement plan were prepared, the operator explicitly selected
`授权接入现有配置并上线（推荐）`. This overrides the credential-change exclusion
only for copying the existing private project's NAI_NOVELAI_MCP_URL and
NAI_NOVELAI_MCP_TOKEN into the production operator environment, publishing the
reviewed API/web fix and restarting the API. Preserve all unrelated settings,
especially Codex advice. Only non-billable MCP discovery is authorized for
verification; no image/advice request or automatic paid retry is authorized.

## Acceptance Criteria

- [ ] Positive editing visibly distinguishes `画风`, `公共` and `人物`.
- [ ] Users can add, edit and remove several characters independently; editing
  or removing one entry preserves its siblings and order.
- [ ] Character descriptions reach the provider as native independent
  characters, with style/shared text applied through the base prompt.
- [ ] The negative editor is accessible from a distinct side tab and reserves
  no horizontal content area while inactive. Switching tabs preserves text.
- [ ] Section data and character boundaries survive generation history and
  reuse. Legacy flat history populates the shared section without data loss.
- [ ] Tag insertion targets an explicit section/character, including after
  character removal. Logout/session expiry clears protected drafts.
- [ ] Unsupported native provider schemas fail before a paid tool call, without
  retries or fallback that merges characters.
- [ ] Frontend lint/type-check, env-free build and relevant offline backend
  checks pass; desktop/mobile runtime acceptance is recorded as pending.

## Follow-up: Prompt Tags and Weights

The operator requested on 2026-10-14 that style, shared, character and global
negative prompt inputs become tag views on textarea blur. Each tag shows its
weight at the right with up/down buttons that change it by exactly 0.1.
Clicking a tag or its container must never reopen text editing: only a
bottom-right `手动编辑` button does that. Advice is outside this change.

- Keep the original draft string unchanged on blur. Weight changes must use
  NovelAI syntax and flow through the existing request/history strings.
- Use one reusable editor and one parser/weight helper for all prompt fields.
  Preserve grouped/escaped text, original separators and unrelated tags.
  Unrecognized or incomplete syntax remains visible and manually editable.
- Tag insertion, history reuse, independent character IDs, panel switching,
  keyboard focus and protected-state cleanup retain their current behavior.
- Keep frontend automated/browser tests disabled. Verify with source review,
  lint/type-check, a fresh env-free production build and public HTTP checks.
- Publish a fresh web-only release under the existing deployment authorization.

## Follow-up: Style Experiment

Add a `画风实验` control to the right of the style heading. The operator
requested selecting several style tag occurrences, setting a minimum,
maximum and step, then generating every Cartesian combination of their
weights in ascending order. A supplied seed is reused throughout; otherwise
only the first request is random and subsequent requests use its effective
seed. See `style-experiment-design.md` for the execution contract and
`research/style-experiment-contract.md` for repository evidence.

- Each selected occurrence has its own min/max/step. Use precise decimal
  arithmetic and include `min+n*step <= max`, without an off-step endpoint.
  The last selected occurrence varies fastest. Duplicate tag texts remain
  independently selectable; original/unknown syntax is not guessed.
- Show total groups and total images before Start, retaining the existing
  per-group sample_count. Freeze all generation settings and prompt sections
  at Start, including independent character boundaries. Draft edits cannot
  alter the active experiment. Leave the draft's seed and style unchanged.
- Submit one combination at a time through GenerationStore and the existing
  API. Fetch its images before advancing, show labeled comparison results,
  progress and the effective seed, and provide Stop for future submissions.
- Stop cannot cancel an accepted task. Halt on failure, uncertain POST,
  polling error or missing images; preserve prior results and existing
  uncertainty/history checks. Never automatically re-POST a failed step.
- Enumerate lazily without allocating the whole product or silently dropping
  combinations. Show one result image with left/right navigation; retain
  produced images in current browser memory until explicit clear/logout/disposal.
  Reload stops further work; individual task parameters still use existing
  durable history.
  Starting a valid new experiment explicitly replaces the prior comparison;
  disclose this before Start, and preserve prior results if validation fails.
- Verify through source review, lint/type-check, an env-free build and public
  HTTP checks; no frontend automated/browser tests or paid provider calls.
  Publish the completed frontend under existing deployment authorization.

Acceptance: two tags with three values each produce all nine distinct
requests, with only those style weights varying; a null first seed is locked
from its first observed effective_seed, and every later request uses it.
Stop/error/logout prevent a successor POST. Completed images remain labeled
and downloadable without being revoked by advancing to the next group.

## Follow-up: Compact Neutral Weights

On 2026-10-15 the operator requested removing redundant numeric emphasis
when an explicit weight adjustment returns to 1.0. For example,
`1.1::artist:meion::` adjusted down becomes `artist:meion`, and 0.9 adjusted
up has the same result. Default plain tags continue to display weight 1.0.

- Apply the same rule in the shared absolute-weight writer so ordinary
  prompt controls and style experiment combinations agree. Exact decimal
  equivalents of 1 normalize to the same neutral behavior.
- Remove only the selected outer numeric wrapper, retaining its exact body,
  internal emphasis, whitespace, escapes, sibling text and delimiters.
  Setting an already plain tag to 1 leaves its source unchanged.
- Blur/manual editing alone does not rewrite drafts. Unknown or incomplete
  expressions retain the existing conservative handling.
- Neutral-only experimental ranges must not budget nonexistent wrappers in
  preflight length checks; preserve lazy enumeration and source-span safety.
- Retain all prior verification restrictions and publish a fresh web-only
  release under existing authorization.

## Follow-up: Sampler Choices

On 2026-10-15 the operator reported that sampler ID has no options. Provide
a visible dropdown of the seven pinned-source sampler names and IDs, with
an explicit manual-ID option. Keep arbitrary historical/custom values and
the current draft as the source of truth; selecting manual entry must not
discard its current value. Do not invent a model-specific compatibility
matrix or change the initial blank sampler into an automatic choice.
Static choices supplement the existing string contract. Preserve normal
generation, history reuse and frozen experiment settings. Publish web-only
under the retained authorization and verification restrictions.

## Follow-up: Definite Submission Refusal

On 2026-10-15 the operator repeatedly received the unknown-submission message.
Logs/source identify HTTP 503 before enqueue while the production image
provider is unconfigured. Handle the exact generation-POST pair
503/provider_unavailable as a definite rejection, show that image generation
is not configured, and do not set the unknown-result acknowledgement lock.
Unknown transport/5xx outcomes retain the existing protection. Neither case
automatically retries a paid POST, and experiments halt rather than advance.
Independent review found that the route's broad RuntimeError catch also
maps executor submission failures after history creation to this same pair.
Narrow it to a dedicated not-configured exception raised only at the initial
executor guard, with offline regressions proving other RuntimeErrors cannot
claim pre-acceptance refusal. The safe frontend classification requires this
backend correction first; the previous web-only publication plan is superseded.
Prepare a matched API/web release and finish all offline/static checks.
The operator has now authorized production image configuration and the
combined restart/switch under the narrow exception above. Do not publish the
new frontend against the old broad catch.
See `research/submission-rejection.md` for evidence and boundaries.

## Follow-up: Experiment Image Navigation

On 2026-10-15 the operator requested left/right arrow navigation of retained
style-experiment images instead of displaying the whole comparison grid.
Replace the paginated group/image grid with a single-image viewer. Navigate
in generation group order, then image order within each group. Retain the
current group's weights, seed, status, parameters and image download.

- Place accessible previous/next arrow buttons on the viewer's sides, show
  the current position and disable the corresponding arrow at each end.
  Left/right keyboard navigation is scoped to the viewer, never a global
  handler that interferes with prompt editing.
- Keep a stable image area with contain sizing to compare without layout
  jumps or cropping. Render one image at a time on desktop and mobile.
- Appended results do not move the selected image. Clear/new experiment
  resets browsing; protected-state cleanup retains existing URL ownership.
  Failed/empty groups remain reachable with their metadata and errors, using
  a placeholder entry rather than silently dropping them.
- Navigation reads the existing archive only; it must not fetch, generate,
  retry, mutate the draft, clear archived URLs or change experiment execution.
  Scope is StyleExperiment.tsx and its CSS only. Source review, lint/types,
  fresh env-free build and web-only publication follow existing authorization.
  No frontend/helper/browser tests, paid calls or credential changes.

## Decisions and Provider Evidence (Original Native Characters)

- A non-billable MCP initialization and tool listing on 2026-10-14 confirms
  deployed `generate_image.character_prompts` accepts an optional array of
  objects. No image tool was called; see `research/deployed-mcp-schema.json`.
- Public provider v0.4.0 and current source define independent character
  `prompt`, `negative_prompt` (or `uc`), `x`, `y` and `enabled`. Defaults are
  empty negative prompt, centered `x=y=0.5`, and enabled. Preserve those
  defaults; expose only positive character editing in this revision.
- Native characters are limited to the six verified non-inpainting V4,
  V4.5 and V5 model IDs. Reject other model IDs when characters are supplied
  before submitting a paid request. Flat requests retain editable IDs.
- Bound the workspace to six characters, each at most 3000 characters, and
  a combined style/shared base of at most 3000 characters. Six is a workspace
  policy, not a claimed upstream hard limit. Empty editor cards are omitted.
- The previous clarification and the operator's native-character selection
  authorize this behavior. No remaining product choice blocks implementation.
