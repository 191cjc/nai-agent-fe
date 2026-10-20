# Native Character Prompt Editor

## Follow-up: Per-section Assistant (2026-10-16)

The operator requests a button on each prompt section that opens a compact
anchored popover with AI advice and prompt-search tabs, while retaining the
left unified advice drawer. Search results must offer one-click append or
replace into the exact opening section. Continue the existing in_progress
editor task and retained implementation/publication authority.

- Cover the fixed shared/character sections and reuse the same helper for
  style and negative prompts. Keep existing section actions and style tests.
- Opening/switching tabs performs no request. AI advice uses an explicit,
  editable consultation containing only the opening section's current text
  and label, submitted only on request. Search uses the existing tag service.
- Show AI suggestion as editable plain text with explicit application actions;
  never apply output automatically. Search candidates expose append/replace.
- Application affects only the exact stable section/card, preserves hidden
  state, validates relevant per-field/composed limits atomically, and works
  before generation settings are complete. Missing/reset targets cannot be
  silently reassigned. Failures leave all draft content intact.
- Popover avoids clipping in the bottom drawer, supports narrow/short screens,
  keyboard tabs, Escape/outside close and safe focus. Close on owner disclosure
  hiding, session/reset/removal; discard stale responses on close/switch/reset.
- Keep left search/advice state independent, rate-limit feedback and safe
  errors intact. No backend contract/migration/dependency or generation-flow
  change. Web-only publication preserves live API work.
- Verify lint/TypeScript, source review and a fresh env-free build; no
  frontend/helper/browser automated tests or paid advice/generation probes.

## Follow-up: NovelAI-aware Advice (2026-10-16)

The operator requests that advice explicitly targets NovelAI prompts, prefers
tags compatible with NovelAI, and explains the selected section's role so
section suggestions are usable in that destination. Apply this to common AI
advice and all section helpers, including style/negative and both distinct
shared/character other sections. The editable section consultation must visibly
name NovelAI, its exact destination and appropriate content scope. Preserve
only-current-section context, explicit submission/application, existing settings
questions, plain-text suggestion and all runtime restrictions.

Acceptance: common advice has NovelAI/Danbooru-oriented instructions; each
section's consultation asks for relevant English comma-separated tags with no
headings/explanations inside the suggestion. Avoid unsupported claims that tags
were searched/verified. No implicit other sections/images/history, API/schema/
DB/runtime/dependency changes or paid acceptance probe. Existing offline backend
checks and static web/source/build validation, then matched API-first release
after idle/backup checks under existing authorization. See novelai-advice-design.md.

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
- Image uploads, references and Vibe transfer. Automatic character positioning
  is not exposed by the inspected provider. Manual position dragging is now
  included by the follow-up authorization below.
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

## Follow-up: Restore Latest History on Entry

On 2026-10-15 the operator requested restoring the latest history item's
prompts and settings automatically each time they enter the workspace.

- On authenticated page entry or login, load the newest saved history item
  and apply the existing reuse semantics: style/shared/negative prompts,
  independent characters and all generation settings, including effective
  seed. Preserve legacy flat history and arbitrary sampler/resolution values.
- No history leaves the fresh defaults. History failures remain visible and
  leave the draft usable. Do not generate, resume jobs, fetch images or retry
  paid work as part of restoration.
- Restore once per authenticated entry. Ordinary history refresh/pagination,
  generation completion and a failed logout must not reapply history.
  A late response must not overwrite user edits, manual reuse, new operations,
  logout/reset/disposal or a different authenticated session.
- Frontend-only scope, existing web publication authorization and static
  validation restrictions apply: no frontend/helper automated tests, browser
  automation, paid calls, credential or API changes.

## Follow-up: Left Tool Drawers

On 2026-10-15 the operator requested moving history, prompt lookup and AI
advice out of the bottom drawer, below Settings in the left navigation, with
the same left drawer behavior as Settings.

- Show left controls in order: Settings, History, Prompt Lookup, AI Advice.
  Use visible/accessible names `生成设置`, `历史记录`, `提示词查询`, `AI 建议`.
  Each tool opens the left drawer area; only one panel is open at a time.
  Clicking the active control again, its close button or Escape closes it.
- Match the existing settings panel's desktop width and narrow-screen left
  overlay/backdrop behavior. Remove the bottom tool drawer and its reserved
  height so editor/results can use the available main area.
- Switching/closing panels preserves draft, settings manual-entry state,
  history page, tag query/results/target and advice input/output. It does not
  issue tool requests. Explicit search/advice/history actions keep their
  existing behavior; uncertain-submit history action opens the left history.
- Keep accessible names, expanded/control relationships, keyboard focus and
  hidden-panel behavior. Preserve latest-history entry restoration and all
  existing generation/experiment/image behavior.
- Scope App.tsx and styles.css; keep frontend/static-only validation and
  existing web publication authorization. No browser/helper tests or paid calls.

## Follow-up: Draggable Character Positions

On 2026-10-15 the operator chose to implement draggable character positioning
first, following the position-preview recommendation. Tag disabling and
action/clothing categories remain design discussion only.

- Show a canvas-proportional position preview near the character editors,
  with stable numbered markers for each character. Support mouse/touch drag,
  keyboard adjustment and reset to center. Provide a way to select each
  character when default centered markers overlap.
- Keep each position with its character through edits/removal, submission,
  parameter history, manual/automatic reuse and frozen style experiments.
  New characters and old history default to x=y=0.5. Empty draft cards remain
  omitted from generation. Positions guide character placement, not limb pose.
- Validate finite numeric x/y in the provider-supported inclusive 0.1–0.9
  range on both layers; clamp pointer movement to it. Preserve separate native
  character prompts, model limits and all existing generation/no-retry guards.
- Extend the API and adapter; deliver the backend before the new frontend so
  position changes reach the provider. Keep existing provider configuration.
  Follow existing private-backup and no-active-job restart precautions.
- Source/static frontend checks only, meaningful offline backend regressions,
  fresh env-free build and production verification. No frontend/helper/browser
  tests, paid calls, credentials changes or image persistence.

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

## Follow-up: Private Seven-Day Images (2026-10-15)

The later durable-experiment follow-up below supersedes only this section's
earlier no-background-scheduler/no-continuation restriction.

The operator selected private server image storage for seven days, surviving
refresh and API restart, to make style testing practical. Earlier exclusions
on image persistence are superseded for this follow-up. Use
`image-retention-design.md` as the owning cross-layer interface.

- Save new successful ordinary and experiment images privately for seven days
  from completion; serve only their authenticated owner. Expiration is durable
  across restarts, with automatic cleanup and no early capacity eviction.
- Preserve experiment identity, exact varied weights, ordinal/total, saved
  requests and seeds. History can reopen one image at a time with left/right
  comparison after refreshing or restarting, with lazy bounded retrieval.
- Keep ordinary history viewing/download, reuse and latest-entry restoration.
  Expired images retain reusable parameter/group metadata and a clear message.
- No automatic paid continuation or retries, server-side batch scheduler,
  public links, browser persistence, old-image recovery or unrelated features.
- Preserve existing offline/static verification restrictions and publish a
  matched API-first release under existing deployment authorization.

Acceptance: new images and saved experiment order/weights/seed remain readable
by the same owner after process/page restart; other owners get 404. At seven
days images become unavailable and are cleaned while parameters remain. New
paid work is refused safely if storage cannot reserve capacity. Closing,
refreshing, historical viewing or service restart never submits paid work.

## Follow-up: Background Style Experiments (2026-10-15)

The operator requests that a failed group does not stop later combinations,
closing the page does not stop execution, and the next visit reconnects to the
same experiment. This supersedes earlier browser-only scheduler exclusions.

- Explicit Start freezes one complete plan/settings/seed on the server.
- Success or failure advances to the next combination automatically; never
  automatically retry the same combination, including an uncertain result.
- Only explicit Stop prevents later groups; the already accepted current group
  may finish. Completion reports success/failure counts and errors.
- Closing/reloading/logging out detaches the UI; server execution continues.
  Re-entry attaches through read-only progress retrieval, without duplicating
  paid requests or overwriting the user's draft. Retained images remain private
  for seven days and accessible through lazy left/right historical comparison.
- Restart recovers persisted progress and never replays an interrupted group.
  Preserve ordinary generation safeguards and all native character/settings.
- Keep existing static frontend/offline backend verification restrictions and
  paired API-first publication authority. No credential changes or paid probes.

Acceptance: a fake batch whose first/middle group fails still attempts each
later combination once with the original seed/settings. Removing all browser
observers does not change progress; re-entry shows the same run. Stop blocks
new groups, restart reconciles the accepted group once, concurrent create does
not duplicate a run, and another owner cannot see/control its data.

Technical interface: durable-experiment-design.md; no unresolved product choices.

## Follow-up: Visible Image-service Balance (2026-10-16)

The operator requests a warning when a request costs credits, or at least the
current remaining balance at the top. Implement the reliable minimum: NovelAI
image-service Anlas in the header, with fixed/purchased breakdown, successful
update time, manual refresh and independent refresh on entry, ordinary terminal
results and experiment progress. The operator explicitly confirmed NovelAI
image Anlas, rather than advice API billing.

Never label a request free/paid from an estimate or attribute shared account
changes to one local user/request. Actual per-request charges are not exposed;
V5 estimates can be zero while exhausted free capacity causes billing. Keep
last known balance with visible error/freshness, render true zero and clear
protected data on session cleanup. Account errors cannot block/retry generation.

Acceptance: authenticated users see normalized Anlas at the top, including
narrow screens. Coalesced refresh observes later deductions even if activity
overlaps an old query. Invalid/missing data never becomes zero or fresh cached
success. Unauthenticated requests cannot query the provider. Preserve existing
generation/experiments; fake-only backend/static web checks, then API-first
publication after idle/private-backup checks under existing authority. See
account-balance-design.md.

## Follow-up: Faster Comparison Revisit (2026-10-15)

The operator asks about browser image caching because arrow navigation reloads
previously viewed images. Retain recently viewed successful images in a bounded
in-page memory cache (32 entries/64 MiB of image bytes), so revisiting within
capacity avoids downloading PNG bytes again. Preserve fresh authenticated group
metadata, expiry, selected-image/download consistency and all run behavior.
Close/replacement/logout/session expiry/disposal clears URLs and memory;
refreshing the browser starts fresh. No persistent/public/HTTP disk cache or
whole-experiment download. Source/static verification and web-only publication
follow existing authority; viewer-cache-design.md owns the detailed boundary.

## Follow-up: Canvas-Centered Bottom Prompt Drawer (2026-10-16)

The operator requests NovelAI's image-first layout: the main body is a canvas,
prompt inputs move into a collapsible drawer below it, and Generate stays at
the very bottom. Replace editor/results stacking with a shared main canvas for
the current generation or selected historical comparison. Preserve the existing
left tool drawers, all structured prompt/tag/character/position controls,
generation locks, experiment Stop/reattachment and private image/cache lifecycle.

Acceptance: images dominate the available center area; prompt drawer starts
expanded and can collapse without losing edit/configuration state; Generate,
uncertain-result actions and experiment controls remain reachable while it is
closed. Multiple current images can be selected on the canvas without new
downloads, and saved comparison arrows/cache continue working. History reuse
opens the prompt drawer; history status opens the current result. Desktop and
narrow/short mobile layouts keep the toggle/action bar reachable. Verify via
source/static checks and a fresh build; existing no-browser/no-paid-call and
web-only publication authority applies. See canvas-layout-design.md.


## Follow-up: Experiment Zero Weight (2026-10-16)

The operator requires weight 0 in style experiments to mean removal of the
selected occurrence. Keep its zero weight in comparison metadata, preserve
unselected duplicates, and match browser/server rendering. Reject a plan
that could leave both style and shared prompts empty before starting.
Existing durable runs keep their frozen original semantics. See
zero-weight-design.md for the scoped contract and release gate.


## Follow-up: Automatic Character Position (2026-10-16)

The operator reports new MCP automatic positioning: omit x/y or use the
explicit auto_character_position flag. Add automatic/manual selection while
preserving manual positions, history and frozen experiment mode. Ignore the
external documentation path. The initial no-restart instruction was superseded
by the operator's explicit "现在可以重启服务" authorization; complete checks,
clean build and idle/backup preflight before API-first publication. See
auto-character-position-design.md and the new configured-provider discovery
snapshot. This supersedes earlier claims that the configured provider lacks
automatic positioning. No paid verification calls.

## Follow-up: Prompt Sections and Snapshots (2026-10-16)

The user requests public 场景/其他 and, for each independent character,
角色/上半身服饰/下半身服饰/动作/标签/特殊/其他. Each section offers 隐藏
(retained but excluded from generation), 保存 and 导入. Multiple selected
sections can form one named snapshot; a global importer accepts multiple
snapshots. The user explicitly chose append/replace at import time, with
append as default. Snapshots are private durable account data; character
imports expose target mapping. Import preserves current hidden states and
only changes selected destination text. Existing unsplit text restores
verbatim in 其他. History/reuse preserve hidden sections and character positions;
active experiments retain their frozen prompts. See prompt-sections-design.md
for exact contracts, atomic application, compatibility and acceptance checks.

## Follow-up: Individual Hidden Tags (2026-10-16)

The operator requests per-tag temporary hiding in addition to section hiding.
They explicitly selected whole-line // comments and one tag per line on blur.
Each tag can hide/restore without losing its weight; hidden chips remain visible
and recoverable. Manual text shows comment markers, and blur safely formats
expressions. Hidden text is excluded from generation and experiment candidates,
but retained in history and snapshots. Appended search/advice/import text stays
outside prior comment lines. Preserve exact legacy frozen runs. See
hidden-tags-design.md for bounded syntax, persistence and release contracts.

## Follow-up: Load All Experiment Images (2026-10-20)

The operator requests one button to begin loading every experiment-result image
so arrow comparison avoids individual image downloads. Add explicit background
loading with progress, cancel, cached reuse and continuation after individual
image failure; skipped/expired/capacity outcomes remain visible. Keep comparison
usable and retain the live server experiment. Session-only bounded memory and
raw server expiry remain unchanged in principle. See preload-images-design.md.

## Follow-up: Overlay Prompt Drawer (2026-10-20)

The expanded bottom prompt drawer must cover the main canvas rather than
compress it. Canvas/image sizing stays the same when opening/closing the
drawer; prompt content scrolls within the overlay. Keep the toggle, Generate,
operation recovery/progress/Stop and left tools reachable, with unchanged
editor/form/focus behavior. See overlay-prompt-drawer-design.md. Publish only
the frontend and retain the running API.

Full-height clarification: the operator requires the expanded drawer to cover
the entire image and use the whole available main viewport, not the former
28dvh/300px bottom sheet. Fill the canvas stage from its top to the persistent
bottom controls, with an internally scrolling editor and unchanged underlying
canvas sizing. This supersedes the first overlay release's small body height.

## Follow-up: Per-section AI Translation (2026-10-20)

Add AI 翻译 right of AI 建议 in every section helper. Users can ask for Chinese
meanings of that section's existing prompts. Show current tags, allow a short
question and present read-only explanations without editing the draft. Keep
section/session ownership and explicit requests; distinguish old-source results
after edits. See section-translation-design.md for frontend and runtime guidance.

## Follow-up: Restore AI Service Configuration (2026-10-20)

Advice/translation503 was traced to a missing production AI key. The user
authorized reusing AiQQ AI configuration and requests the later key-edit
location. Support its custom HTTPS endpoint and selected model with optional
backend settings, privately copy the three fields once, and release the API
without changing AiQQ or making a real model call. See advice-config-design.md.
