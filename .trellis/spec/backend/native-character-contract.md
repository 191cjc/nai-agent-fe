# Native Character Prompt Contract

## Scope / Trigger

Use when changing the structured prompt editor, GenerationRequest, saved
parameter JSON, or the NovelAI MCP adapter. The browser sends workspace fields;
only the API maps them to the provider. Native character descriptions must
remain separate through editing, persistence, reuse and provider submission.

## Signatures

- `GenerationRequest` retains `positive_prompt` as shared scene text and adds
  `style_prompt: str = ''` and `character_prompts: list[CharacterPrompt] = []`.
- `CharacterPrompt` contains nonblank `prompt: str` and strict finite
  `x: float = 0.5`, `y: float = 0.5`, inclusive within `[0.1, 0.9]`.
  Omission defaults independently; explicit null, booleans, numeric strings,
  nonfinite numbers and out-of-range values fail validation.
- `GenerationRequest.base_prompt` composes only style and shared scene text.
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
  For each ordered character send
  `{prompt, negative_prompt: '', x, y, enabled: true}` through the
  optional `character_prompts` argument. Global negative_prompt is unchanged.
  Forward each validated coordinate exactly and preserve order; the verified
  wrapper bounds are 0.1–0.9, not 0–1.
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
- The provider source forces coordinate mode when characters exist, with all
  omitted coordinates defaulting to the center. This is centered default
  positioning; do not claim automatic placement. Public source supports the
  mapping, while the deployed schema alone cannot prove internal version,
  successful model availability or generated image quality.
- Save the entire validated request in the existing private settings_json.
  No schema migration or image persistence is needed. Reuse restores style,
  shared text and ordered characters with positions; old native records with
  omitted axes default to center. Legacy flat text goes into shared.
- Native rollout is API first, then frontend. An old API ignores unknown
  fields, so a frontend-only release could silently discard characters.
  Coordinate releases also require API-first order: the previous native API
  ignores x/y and hardcodes center. Retain the coordinate API during web
  fallback, since already-open new tabs may send positions.
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
- Review the additive deterministic OpenAPI snapshot and matching browser
  types together. No schema generation may create a DB or contact providers.
- Frontend source review checks stable card identities, explicit tag targets,
  fallback after targeted-card removal, reuse/reset, side-tab keyboard focus
  and hidden panel layout. Lint/type-check and env-free build are allowed;
  frontend automated/browser tests remain excluded by operator instruction.

## Wrong vs Correct

- Wrong: send raw downstream `v4_prompt`, `characterPrompts`, `char_caption`
  or `center` objects as MCP arguments.
- Correct: send MCP character_prompts children with prompt, negative_prompt,
  x, y and enabled; the provider owns downstream caption serialization.
- Wrong: use array indices as persistent tag insertion targets or serialize
  client card IDs into the browser API.
- Correct: keep stable draft-only IDs, serialize prompt and x/y coordinates,
  and reset invalid targets to shared on removal/reuse/session reset.

- Wrong: add draggable markers while leaving the adapter hardcoded to center.
- Correct: preserve x/y across browser snapshots, validation, storage and MCP.
