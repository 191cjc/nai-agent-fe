# Design: Native Character Prompt Editor

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
