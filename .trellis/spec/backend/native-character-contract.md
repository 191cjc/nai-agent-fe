# Native Character Prompt Contract

## Scope / Trigger

Use when changing the structured prompt editor, GenerationRequest, saved
parameter JSON, or the NovelAI MCP adapter. The browser sends workspace fields;
only the API maps them to the provider. Native character descriptions must
remain separate through editing, persistence, reuse and provider submission.

Fixed shared/character editor sections and hidden states follow
[Prompt Sections](./prompt-sections-contract.md): optional private metadata
must exactly project to the unchanged effective fields below. Fully hidden
people stay in metadata; they never relax CharacterPrompt nonblank validation
or enter MCP. Old unsplit text restores in 其他 without semantic inference.

Whole-line per-tag comments and raw/effective projections follow
[Individual Hidden Tags](./prompt-comments-contract.md). Syntax is opt-in per frozen request;
absent/false preserves the legacy contracts below.

## Signatures

- `GenerationRequest` retains `positive_prompt` as shared scene text and adds
  `style_prompt: str = ''` and `character_prompts: list[CharacterPrompt] = []`.
- `CharacterPrompt` contains nonblank `prompt: str` and strict finite
  `x: float = 0.5`, `y: float = 0.5`, inclusive within `[0.1, 0.9]`.
  Omission defaults independently; explicit null, booleans, numeric strings,
  nonfinite numbers and out-of-range values fail validation.
- `GenerationRequest.base_prompt` composes only style and shared scene text.
- `GenerationRequest.auto_character_position: bool = False` is strict: no
  null, string or number coercion. Omitted mode in old callers/history/run
  definitions stays manual. Character x/y remain validated/defaulted as above
  and stored even in automatic mode, for lossless switch-back and history.
- `POST /api/generations` accepts these additive fields; generation/history
  responses return them under `parameters`. Old saved settings_json supplies
  empty style and no characters through model defaults.

## Contracts

- A blank style preserves the existing positive_prompt exactly for legacy
  compatibility. Otherwise join trimmed nonempty style/shared parts with `, `.
  The composed base must be nonblank and at most 3000 characters. Each
  individual style/shared/global-negative field is at most 3000 characters.
- Accept at most six nonblank character descriptions, each at most 3000
  characters. This is a workspace bound, not a verified NovelAI hard limit.
  The UI may keep empty draft cards but omits them from the submitted list.
- With characters, accept only these verified ordinary text-to-image IDs:
  `nai-diffusion-4-full`, `nai-diffusion-4-curated-preview`,
  `nai-diffusion-4-5-full`, `nai-diffusion-4-5-curated`,
  `nai-diffusion-5-full`, `nai-diffusion-5-curated`.
  Preserve free-form model/sampler inputs for requests without characters.
- The MCP base `prompt` is base_prompt, not a concatenation of characters.
  Manual positioning sends each ordered child as
  `{prompt, negative_prompt: '', x, y, enabled: true}`; forward validated
  coordinates exactly (0.1–0.9, not 0–1). Explicitly send
  `auto_character_position=false` when its optional advertised schema accepts
  false. Legacy/missing/incompatible flag schemas retain coordinate-only
  manual compatibility. Global negative_prompt and character order stay intact.
- Automatic positioning requires the advertised flag to accept true, sends
  `auto_character_position=true` and ordered children with prompt,
  negative_prompt and enabled, with x/y entirely absent. Stored workspace
  coordinates are not forwarded in this mode. With no characters keep the
  original eleven flat MCP fields, irrespective of the stored mode.
- Before a paid tool call, require tools/list to advertise an object-array
  character_prompts argument, including its deployed nullable anyOf form.
  Missing/incompatible support fails with unsupported_character_prompts;
  never flatten, silently omit characters or retry an uncertain paid call.
  Flat requests retain the original eleven MCP arguments.
- The native schema check conservatively recognizes the verified untyped
  object-array form. It ignores annotations, checks declared integer
  minItems/maxItems against the requested count, and rejects unknown
  validations or constrained item schemas such as properties/required or
  additionalProperties:false. This intentionally fails closed rather than
  claiming to validate arbitrary future JSON Schema.
- On 2026-10-16 fresh initialize/tools/list against the configured application
  provider verified `auto_character_position` as nullable anyOf boolean/null.
  The operator confirmed new omission/explicit-mode semantics. This supersedes
  earlier centered-only source research for this boundary. Recognize verified
  boolean/nullable-anyOf forms conservatively, ignoring annotations and
  rejecting unknown constraints. Unsupported automatic mode fails before
  tools/call with unsupported_auto_character_position; never silently center.
  Keep fresh per-generation discovery; no long-lived schema cache. Discovery
  and the reported semantics do not establish real generated placement quality.
- Save the entire validated request in the existing private settings_json.
  No schema migration or image persistence is needed. Reuse restores style,
  shared text and ordered characters with positions; old native records with
  omitted axes default to center and omitted mode to manual. Preserve selected
  mode through history/reuse and frozen server-run settings. Legacy flat text
  goes into shared. Same-id run compatibility normalizes only a missing saved
  parameters.auto_character_position to false; changed mode/other definition
  keys still conflict, and stored definitions remain byte-identical.
- Native rollout is API first, then frontend. An old API ignores unknown
  fields, so a frontend-only release could silently discard characters.
  Coordinate releases also require API-first order: the previous native API
  ignores x/y and hardcodes center. Retain the coordinate API during web
  fallback, since already-open new tabs may send positions.
  Automatic mode likewise requires API-first rollout and retaining its
  compatible API on web fallback: older APIs ignore the mode and send manual
  positions. Complete independent verification, clean build and private online
  backup/idle preflight before an authorized coordinated release.
- API downgrade compatibility includes saved JSON, not only SQLite version.
  Style-only records can have positive_prompt='' and fail the old API's
  minimum-length validation when history is read. Prefer a forward fix or
  keep the new API during frontend fallback; keep generation unavailable while
  that older UI cannot preserve native fields. Downgrading the API requires
  verifying saved inputs against its model, or an explicitly accepted restore
  to its compatible snapshot that loses newer writes.

## Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Old flat request/history without new fields | Empty style/list defaults; original shared prompt preserved |
| Shared blank, style supplies nonblank base | Valid if the composed base meets bounds |
| Blank base, even with characters | Reject validation; characters do not supply shared base content |
| Composed base over 3000 or more than six characters | Reject validation before provider execution |
| Blank/oversized character description | Reject validation; do not silently alter sibling entries |
| Omitted character axis in request or old native history | Default that axis to 0.5 |
| Omitted positioning mode in request/history/run | Manual default; frozen behavior preserved |
| Null/string/number positioning mode | Reject strict validation |
| Automatic mode with supporting MCP schema | Send true and omit all child x/y |
| Automatic mode with missing/incompatible MCP support | unsupported_auto_character_position; zero tools/call |
| Manual mode with old MCP schema | Keep coordinate payload; omit unsupported optional mode flag |
| Coordinate 0.1 or 0.9 | Accept inclusive boundary |
| Null, bool, string, nonfinite or out-of-range axis | Reject validation before provider execution |
| Native characters with legacy/unknown/inpaint model ID | Reject validation before a paid call |
| Native list absent or not an object-array in provider schema | Job fails safely with unsupported_character_prompts; zero tools/call |
| Provider credentials absent | Existing safe provider_unavailable behavior |
| Old API reads new style-only saved input | Incompatible downgrade despite unchanged SQLite schema; retain new API or restore an accepted compatible snapshot |

## Good / Base / Bad Cases

- Good: style `watercolor`, shared `two people, garden`, and two character
  descriptions produce base `watercolor, two people, garden` and two ordered
  MCP character objects. Distinct `(0.2, 0.4)` and `(0.8, 0.6)` positions
  survive settings_json, history/reuse and provider submission.
- Base: old history containing only `positive_prompt: 'blue hair'` restores
  `blue hair` in shared with empty style and no native characters.
- Good: switching automatic -> manual restores saved `(0.2,0.4)` and
  `(0.8,0.6)`; automatic provider children contain neither x nor y, even when
  those coordinates are stored for reuse. No characters means no new MCP flag.
- Bad: join the two character prompts into base text, accept a legacy model
  that drops native captions, or describe default centered coordinates as
  automatic placement.

## Tests Required

- Offline generation tests validate base composition/bounds, native model
  restrictions, count/blank/length limits, legacy defaults, owner isolation,
  strict coordinate types/bounds and structured settings_json round trips
  through restart and backup/restore, including old native JSON with omitted
  coordinates and distinct noncenter ordered coordinates.
- MCP tests assert the exact distinct ordered character objects, global
  negative prompt, original flat payload, and no paid call on missing or
  incompatible native schema. Tests use only MockTransport/fake providers.
- Mode regressions cover strict/default types, automatic omission/manual
  coordinates, nullable schema and incompatible flag rejection, flat legacy
  payload, private metadata/history/backup/restart, frozen experiment mode and
  canonical old-run idempotency with no definition rewrite or paid replay.
- Review the additive deterministic OpenAPI snapshot and matching browser
  types together. No schema generation may create a DB or contact providers.
- Frontend source review checks stable card identities, explicit tag targets,
  fallback after targeted-card removal, reuse/reset, side-tab keyboard focus
  and hidden panel layout. Lint/type-check and env-free build are allowed;
  frontend automated/browser tests remain excluded by operator instruction.

## Wrong vs Correct

- Wrong: send raw downstream `v4_prompt`, `characterPrompts`, `char_caption`
  or `center` objects as MCP arguments.
- Correct: send MCP character_prompts children with prompt, negative_prompt
  and enabled; manual mode adds x/y and automatic mode omits both axes.
  The provider owns downstream caption serialization.
- Wrong: use array indices as persistent tag insertion targets or serialize
  client card IDs into the browser API.
- Correct: keep stable draft-only IDs, serialize prompt and x/y coordinates,
  and reset invalid targets to shared on removal/reuse/session reset.

- Wrong: add draggable markers while leaving the adapter hardcoded to center.
- Correct: preserve x/y across browser snapshots, validation, storage and MCP.
- Wrong: call omitted old saved coordinates automatic, silently downgrade an
  unsupported auto request, or publish the new selector against the old API.
- Correct: explicit stored mode defaults manual; auto uses verified capability
  with no child x/y; coordinate mode remains available with unchanged bounds.
