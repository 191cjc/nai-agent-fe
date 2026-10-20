# Design: Native Character Prompt Editor

> Latest frontend follow-up: section-assistant-design.md owns the per-section
> AI/search popover, explicit target writes and web-only rollout. The existing
> unified left tools, backend advice contract and schema4 remain unchanged.

> Follow-up precedence (2026-10-15): `durable-experiment-design.md` now owns
> server scheduling, continuation, reattachment and schema3 migration. Earlier
> browser-only/no-resume/no-migration exclusions below are historical for that
> boundary. Private seven-day storage remains in scope.

The later `character-position-design.md` supersedes the original centered
coordinate mapping and positioning-UI exclusion below. Other original
contracts remain in effect. The approved `image-retention-design.md` additionally
supersedes all original memory-only/image-persistence exclusions and adds
private seven-day storage plus saved experiment comparisons.

## Change Boundary

The existing editor stores a flat positive/negative pair and the MCP adapter
sends only a base prompt. Native character support already exists in the
deployed tool schema; extend this workspace's typed request, persistence and
UI rather than concatenate characters or alter the remote service.

Expected source changes are `apps/api/src/novelai_api/generations.py`
(validation and composition), `mcp_images.py` (native mapping and capability
gate), the generation/MCP/API contract regressions and OpenAPI snapshot;
`apps/web/src/api.ts` (additive types and error messages), `store.ts` (draft,
tag targets and reuse), `App.tsx` (editors and summaries), and `styles.css`
(compact side tabs and stacked character cards). Authentication, advice,
polling, image handling and database schema remain outside the change.

## Public Request and History

Keep `positive_prompt` as shared scene content and add optional request fields
with response defaults: `style_prompt: string = ''` and
`character_prompts: [{prompt: string}] = []`. Each character prompt is nonblank
and at most 3000 characters; at most six entries are accepted. Positive/shared
and style text together must produce a nonblank base prompt of at most 3000
characters. Allow blank shared text when style supplies the base.

Only style and shared text are composed for the MCP base `prompt`: preserve
the original shared text exactly when style is blank; otherwise join trimmed
nonempty style/shared parts with `, `. Never append character prompts to it.
Keep negative_prompt as the existing global negative string.

The complete validated request already lives in private SQLite settings_json;
the two additive fields require no migration. Old JSON defaults to empty style
and no characters and reuses its positive text in the shared editor. New
records retain section text and character order. Show structured positive
sections in current result parameters and history, with a shared component.

## Native Provider Mapping

For a nonempty character list require a verified non-inpainting model ID:
`nai-diffusion-4-full`, `nai-diffusion-4-curated-preview`,
`nai-diffusion-4-5-full`, `nai-diffusion-4-5-curated`,
`nai-diffusion-5-full`, or `nai-diffusion-5-curated`. Other/unknown models may
silently omit native captions upstream, so validation must reject them when
characters are present. Do not constrain flat requests to these model IDs.

Read the existing tools/list schema before a paid call. Native requests require
character_prompts to accept an array of objects, including the deployed
nullable anyOf schema. Reject absent/incompatible capability with a stable
unsupported_character_prompts failure. Preserve the old 11-field payload for
requests without characters and the no-retry guarantee for uncertain calls.
Recognize the deployed untyped object-array form conservatively, ignoring
annotations and checking any declared integer item-count bounds. Reject
unknown validations and constrained child schemas instead of implementing a
general JSON Schema validator or risking an incompatible paid call.

Forward each ordered character as a distinct object with prompt, empty
negative_prompt, x=0.5, y=0.5 and enabled=true. The provider forces coordinates
when characters exist; do not claim automatic placement or add positioning UI.
Deployed child object details are untyped; public source supplies the mapping,
but no real image output or deployed implementation version is verified.

## Editor and Tag State

Use a compact vertical positive/negative tab pair along the prompt editor's
edge. The positive panel stacks style, shared and character sections; the
negative panel replaces it in the same area. Hidden content occupies no
horizontal column. Use tab roles, roving keyboard focus and visible active
state; tab switching must not discard draft state.

Each character editor has a stable client-only identity and prompt. Provide
add/remove buttons up to the six-entry workspace cap. Keep client identities
out of the request. Ignore blank cards on submission. Store draft content in
GenerationStore and keep panel visibility in component state.

The tag tool exposes an explicit positive destination selector for style,
shared and each character; textarea focus also selects its positive target.
Use character identity rather than array index for the target. On removing
the selected character, fall back to shared; reset/reuse also resets the target.
Global negative insertion remains explicit. Reuse and successful logout/session
expiry replace all structured protected draft state.

## Compatibility and Rollout

New backend fields are additive and old callers/history remain valid. Deploy
the API before the new frontend if publishing this feature: old API versions
ignore unknown fields and would lose native characters. The prior frontend
can connect to the new backend, but omits structured fields from editing and
reuse; keep generation unavailable while using that fallback. Retain old
releases/assets for rollback; do not change production credentials or make
paid calls for verification.

Database schema compatibility alone does not establish API downgrade safety.
New style-only records may save positive_prompt='' with nonblank style_prompt;
the previous API cannot read these records because its old request model
requires positive_prompt length >=1. Prefer a forward fix or keep the new API
when reverting the frontend. A full API downgrade requires verifying every
saved request against the old model or restoring a compatible snapshot with
explicit acceptance of newer-write loss. Never automatically restore the
production DB merely to roll back this additive feature.

## Follow-up Boundary: Latest History on Entry

Workspace currently loads history page zero without restoring a draft. Add
entry initialization in the existing AppStore/history orchestration, invoked
by the workspace entry effect. Reuse GenerationStore.reuse for complete and
legacy-compatible mapping rather than duplicate request-to-draft conversion.
Backend history is already ordered by created_at DESC, id DESC, owner-scoped;
the first item of page zero is the newest submission regardless of status.

Track one-time entry intent separately from history refresh. Guard the
asynchronous load with an entry/session epoch and a draft edit revision (or
equally reliable edit guard); a superseded history response must never be
mistaken for the initial page. Apply only while the same authenticated entry
remains current and no edit/reuse or generation operation intervened. Cancel
on logout start/reset/disposal, preserving the existing failed-logout draft
contract. Reset initialization eligibility on a new protected session, not on
ordinary history refresh or a failed logout/remount. Keep history errors and
pagination/refresh coalescing behavior. No image/job restoration or paid call.
Expected source files are store.ts and App.tsx only, with no UI redesign.

## Follow-up Boundary: Left Tool Drawers

App.tsx currently splits a settings side panel from bottom tool tabs/drawer.
Replace those visibility states with one local active left panel: settings,
history, tags, advice or closed. Put all four rail controls in that order.
Keep the existing SettingsPanel mounted and reuse its left panel/header/
scroll/overlay layout for tools. Keep tool contents mounted while hidden so
switching does not reset their state or dispatch requests. Generation and
tool state remain in existing stores. Preserve the independent workspace
entry initialization effect added in the parallel history follow-up.

Remove obsolete bottom drawer markup and associated CSS/keyboard-tab code.
Use disclosure buttons with native Tab/Enter/Space operation, aria-expanded
and aria-controls (not abandoned tab/tabpanel roles). Escape/close/backdrop
hide the active panel and avoid leaving focus in hidden content. Desktop
uses the settings column; mobile uses its existing anchored overlay and
backdrop with bounded width/scroll. Update narrow tool layouts for this
column, preserving ordinary/experiment images and prompt side tabs.

## Follow-up Boundary: Prompt Tags and Weights

The remaining behavior gap lives in the prompt textarea rendering. Add a
reusable `PromptEditor.tsx` and `prompt-weights.ts` helper under web/src;
integrate them in App.tsx and style them in styles.css. Draft strings remain
the source of truth, so no new API fields, persistence schema, dependencies,
advice behavior or generation lifecycle changes are necessary.

The view transition on blur must not normalize or rewrite the prompt. Parse
with source spans and replace only the selected tag span when its weight is
adjusted. Respect escaped characters and balanced grouped expressions; retain
unrecognized expressions without guessing their meaning. Use NovelAI numeric
emphasis for exact decimal increments, with the compatibility limitation made
clear for older models. Keep weight controls outside labels and use explicit
button types. Only the manual-edit control enters text mode and focuses its
textarea. Newly added blank character editors can begin in text mode.


## Follow-up Design: Experiment Zero Weight (2026-10-16)

zero-weight-design.md owns exact-zero omission, separator/span preservation,
empty/length validation and internal plan-version compatibility. It supersedes
only experiment zero rendering for new runs; ordinary prompt editing and
existing version1 runs retain their previous behavior.


## Follow-up Design: Automatic Position (2026-10-16)

auto-character-position-design.md owns explicit automatic/manual placement,
strict additive mode/default compatibility, MCP schema gating and persisted
run identity. The operator subsequently authorized service restart; use the
scoped design's independent checks, clean build and API-first publication
gates. Historical centered-only claims are superseded by fresh
configured-provider discovery.

## Follow-up Design: Prompt Sections and Snapshots (2026-10-16)

prompt-sections-design.md owns fixed editor sections, temporary exclusion,
strict additive private composition metadata and schema4 owner-scoped reusable
snapshots. The original effective provider fields remain the paid boundary.
The user confirmed selectable append/replace import, default append. Publish
the schema4-compatible API before the web and retain it on fallback.

## Follow-up: Image-service Balance (2026-10-16)

account-balance-design.md freezes the allowlisted authenticated Anlas endpoint,
isolated read-only MCP query, short cache/coalescing and protected header/store
lifecycle. It deliberately does not classify actual per-request cost.

## Follow-up: NovelAI-aware Advice (2026-10-16)

novelai-advice-design.md scopes shared model instructions and editable per-section
consultations to NovelAI/Danbooru-compatible tags. No API/runtime change; retain
explicit current-section context and plain tag text inside the JSON envelope.

## Follow-up: Individual Hidden Tags (2026-10-16)

hidden-tags-design.md defines whole-line comments, conservative formatting,
strict opt-in syntax, raw persistence/effective compilation and unchanged
frozen experiment semantics. This supersedes the earlier no-rewrite-on-blur
rule only for explicit textarea blur; view/history restoration stays verbatim.

## Follow-up: Explicit Image Preload (2026-10-20)

preload-images-design.md owns the explicit bulk-read exception, selection-owned
preload lifecycle, enlarged bounded cache and truthful progress/cancel semantics.
This is frontend-only; default browsing remains lazy and publication preserves
the existing API process and private data.
