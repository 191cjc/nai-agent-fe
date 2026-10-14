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

## Decisions and Provider Evidence (Native Characters)

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
