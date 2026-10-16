# Research: Native character provider contract

> Superseded positioning boundary (2026-10-16): fresh configured-provider
> discovery and operator report establish explicit automatic/manual support.
> See ../auto-character-position-design.md and
> deployed-mcp-auto-position-schema.json. The centered-only evidence below
> describes the previous provider, not the updated automatic mode. After an
> initial no-restart restriction, the operator explicitly authorized restart;
> the scoped design records the coordinated publication gates.

- Query: Does `xinvxueyuan/NovelAI-Image-MCP` accept native independent characters, and what are the exact child fields, ordering, positioning, limits and model constraints?
- Scope: mixed — repository source and specs, public upstream source/docs, and the main session's separately authorized non-billable schema artifact.
- Date: 2026-10-14

## Findings

### Result

The public MCP already accepts the optional **`character_prompts`** argument.
The correct MCP child uses **`prompt`, `negative_prompt`, `x`, `y`, `enabled`**;
`uc` is accepted as a fallback alias for the child negative prompt.
Do not send raw `v4_prompt`, `char_caption`, `center` or `characterPrompts` as
MCP tool arguments: those belong to other internal or downstream contracts.
The list remains ordered and is converted to native NovelAI character captions.
Upstream service extension is unnecessary for independent character boundaries.

**Positioning limitation:** both v0.4.0 and current public source forcibly set
`use_coords=true` whenever the character list is nonempty. Missing `x` and `y`
default to `0.5` for every character. This is **default centered positioning**,
not verified automatic positioning. Neither source exposes `use_coords` through
the `generate_image` MCP signature. Supporting true coordinate-free automatic
positioning through this wrapper would require an upstream change.

### Versions and authoritative source references

Public HTTPS reads used Python `urllib.request` with 15–20 second timeouts;
no credentials, private configuration, provider generation, browser automation
or tests were accessed or run.

- v0.4.0 resolves to commit `aa741854c1eaf4fe971498f57db8b08210bf99b3`.
  [GitHub tag tree API](https://api.github.com/repos/xinvxueyuan/NovelAI-Image-MCP/git/trees/v0.4.0?recursive=1)
- Public `main` at research time resolves to
  `49554a12938ed33856dbd8a9ce11db5f41704123`, committed 2026-10-13;
  its `apps/server/pyproject.toml:3` declares package version `0.5.1`.
  [Commit API](https://api.github.com/repos/xinvxueyuan/NovelAI-Image-MCP/commits/49554a12938ed33856dbd8a9ce11db5f41704123)
- The public latest release tag is `v0.5.1`, pointing to
  `4eef294719a79b9bd08ce0c85f2442ce9bbef472`.
  Current-main observations below are pinned to the main commit above, rather
  than claiming that current-main and the release tag are the same commit.
  [Tag API](https://api.github.com/repos/xinvxueyuan/NovelAI-Image-MCP/tags?per_page=30)

| Source file | Verified purpose / citation |
| --- | --- |
| v0.4.0 `apps/server/src/novelai_image_mcp/tools/generate.py` | MCP signature, permissive child parsing and ordered conversion. [L16–24](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/tools/generate.py#L16-L24), [L50–118](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/tools/generate.py#L50-L118) |
| current `apps/server/src/novelai_image_mcp/tools/generate.py` | Same child fields; model/sampler now typed enums; no positioning flag exposed. [L30–38](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/tools/generate.py#L30-L38), [L60–135](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/tools/generate.py#L60-L135) |
| v0.4.0/current `nai/models.py` | Nonblank character prompt, coordinate bounds, defaults, and request options. [L197–209](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/models.py#L197-L209), [L248–250](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/models.py#L248-L250), [L261–321](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/models.py#L261-L321) |
| v0.4.0 `nai/payload.py` | Native output character arrays, per-character captions, forced coordinates, and model family branch. [L76–104](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/payload.py#L76-L104), [L161–189](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/payload.py#L161-L189) |
| current `nai/payload.py` | Same forced coordinate behavior remains. [L161–189](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/nai/payload.py#L161-L189) |
| v0.4.0/current `nai/constants.py` | Exact model IDs and structured-model membership. [L37–52](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/constants.py#L37-L52), [L131–172](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/src/novelai_image_mcp/nai/constants.py#L131-L172) |
| v0.4.0/current `tests/test_payload.py` | Source evidence, not a locally run test: upstream explicitly expects `use_coords is True` with a character. [L64–73](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/aa741854c1eaf4fe971498f57db8b08210bf99b3/apps/server/tests/test_payload.py#L64-L73) |
| current `apps/docs/source/tools/generate.md` | Child example, first-character focal-subject guidance, V5 claim of testing up to 22 characters. [L61–77](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/docs/source/tools/generate.md#L61-L77) |

The entire `nai/models.py` file is byte-identical at the two reviewed commits
(SHA256 `570fb51e1ec8e8cc475a1c27dc1633e65bc7fa17b2ae9b06d26af45d0c03cd80`).

### Exact MCP child contract

```json
{
  "prompt": "style and common scene text only",
  "negative_prompt": "shared unwanted content",
  "model": "nai-diffusion-5-full",
  "character_prompts": [
    {
      "prompt": "first independent character description",
      "negative_prompt": "",
      "x": 0.5,
      "y": 0.5,
      "enabled": true
    },
    {
      "prompt": "second independent character description",
      "negative_prompt": "",
      "x": 0.5,
      "y": 0.5,
      "enabled": true
    }
  ]
}
```

This example shows only relevant arguments, not a replacement for the existing
11 required workspace adapter fields.

| Child input | Upstream interpretation |
| --- | --- |
| `prompt` | Converted with `str(cp.get("prompt", ""))`; `CharacterPrompt` rejects blank/whitespace-only text. |
| `negative_prompt` | `str(cp.get("negative_prompt") or cp.get("uc") or "")`; empty string default. |
| `uc` | Fallback alias only when `negative_prompt` is falsey. |
| `x`, `y` | Converted individually with `float(cp.get(..., 0.5))`; each must be in the inclusive interval 0.1–0.9. Omitting differs from explicit null, which is invalid for `float()`. |
| `enabled` | Converted with `bool(cp.get("enabled", True))`; true default. Keep the public workspace typed rather than reproducing permissive coercion. |
| `center`, `caption`, `char_caption`, `centers` | Not read by the MCP `_character` parser. Passing them does not substitute for `prompt`/`x`/`y`. |

`character_prompts: null`, an omitted argument, or an empty list become an
empty internal tuple. Each nonempty list is converted left to right by
`tuple(_character(cp) for cp in (character_prompts or ()))`; no sorting occurs.

### Downstream native representation (do not pass directly to MCP)

For each item the wrapper builds:

```json
{
  "parameters": {
    "characterPrompts": [
      {"prompt": "first", "uc": "", "center": {"x": 0.5, "y": 0.5}, "enabled": true},
      {"prompt": "second", "uc": "", "center": {"x": 0.5, "y": 0.5}, "enabled": true}
    ],
    "use_coords": true,
    "v4_prompt": {
      "caption": {
        "base_caption": "style and common text, plus optional provider quality tags",
        "char_captions": [
          {"char_caption": "first", "centers": [{"x": 0.5, "y": 0.5}]},
          {"char_caption": "second", "centers": [{"x": 0.5, "y": 0.5}]}
        ]
      },
      "use_coords": true,
      "use_order": true
    }
  }
}
```

This is the wrapper's verified serializer output, not an independently probed
official NovelAI wire contract. The positive `char_captions` filter disabled
characters; negative captions additionally omit items with an empty child
negative string. `v4_negative_prompt.caption.base_caption` holds the combined
provider negative preset and shared negative text. The workspace scope needs
only a shared negative editor; keep every child negative empty and enabled.

The class default is `use_coords=False`, but the serializer uses
`request.use_coords or bool(characters)` and copies the result into
`v4_prompt.use_coords`. An unused false class default cannot establish
coordinate-free positioning. The existing planner's separate `build_payload`
function accepts `plan.use_coords`; `generate_image` calls the other serializer
through `GenerationRequest` and does not use that planner path.

The wrapper sets `use_order=True` by default and preserves input order. Its
docs call the first character the focal subject. Treat that guidance as
upstream documentation, not a guaranteed visual result without paid testing.

### Model compatibility

Both reviewed versions' `_V4_MODELS` include V4, V4.5 and V5 families. The
ordinary text-to-image allowlist supported by that source is:

```text
nai-diffusion-4-full
nai-diffusion-4-curated-preview
nai-diffusion-4-5-full
nai-diffusion-4-5-curated
nai-diffusion-5-full
nai-diffusion-5-curated
```

The structured family set also contains these dedicated inpaint variants:

```text
nai-diffusion-4-full-inpainting
nai-diffusion-4-curated-inpainting
nai-diffusion-4-5-full-inpainting
nai-diffusion-4-5-curated-inpainting
nai-diffusion-5-full-inpainting
```

The workspace uses `generate_image`, not inpainting. Conservatively admit
only the six ordinary IDs above for character-bearing requests and document
that as the workspace's supported-model subset. A substring or prefix check
would admit unknown/unverified model names.

V3 and Furry3 are outside the structured family set. The serializer still
emits `characterPrompts` unconditionally but does not build `v4_prompt` or
`v4_negative_prompt` for them; the MCP function performs no explicit rejection.
Therefore the workspace must reject native character requests for those
legacy/unknown models before the paid tool call; merely checking that
`character_prompts` exists in the tool schema is insufficient.

### Character-count and prompt-length limits

No maximum character count is enforced in either reviewed MCP signature,
`CharacterPrompt`, or `GenerationRequest.__post_init__`. Neither source
establishes a hard per-character text-length bound. The `n_samples<=8` limit
is an image-count limit and must not be mistaken for a character-count limit.

Current docs say V5 was "upstream tested up to 22 characters"; v0.4.0 docs do
not contain that line. This is not evidence that 22 is an enforced limit or
that V4/V4.5 share it. An official hard limit was not established in this
research. The main session selected a **workspace policy** of at most six
characters, at most 3000 characters per description, and at most 3000
characters in the composed style/shared base prompt. These must be described
as application limits, not asserted NovelAI limits.

### Existing local boundaries and separately collected deployed schema

- `apps/api/src/novelai_api/mcp_images.py:28` declares eleven flat required
  tool fields. `:169` selects the live tool's input schema; `:182` builds only
  those eleven arguments; `:203` performs the single paid `tools/call`.
  Add optional native arguments only when a character-bearing request needs
  them, verify the schema before that call, and never retry or flatten on
  failure.
- `apps/api/src/novelai_api/generations.py:26` currently models a flat
  `positive_prompt`, and `:65` embeds the validated request in history.
  Additive structured fields with defaults can keep legacy history readable.
  These line references describe the research baseline before implementation.
- `research/deployed-mcp-schema.json` was produced by the **main session** on
  2026-10-14 using only `initialize`, initialized notification and `tools/list`,
  with zero paid calls. Its normalized `generate_image_input_schema` declares
  `character_prompts` as `anyOf` an array of objects (items have
  `additionalProperties: true`) or null, default null. It exposes no child
  fields, character cap, or positioning flag. This is live evidence for
  argument availability, not evidence of the deployed internal implementation
  version or successful image output.

## Related Specs

- `.trellis/spec/backend/api-contract.md`: additive typed browser contract,
  deterministic OpenAPI snapshot, no credential/provider details in responses.
- `.trellis/spec/backend/quality-guidelines.md`: fake-only backend regressions,
  no paid or credential-bearing automated checks.
- `.trellis/spec/backend/provider-adapter-contract.md`: verify actual provider
  wire fields rather than guessing from browser API names.
- `.trellis/spec/frontend/workspace-contract.md`: explicit tag insertion,
  protected-state reset, no frontend automation/browser tests for this task.
- `.trellis/tasks/10-14-native-character-prompts/prd.md`: independent character
  boundaries are mandatory. The research-baseline statement requiring verified
  automatic positioning needs correction to acknowledge the actual default
  centered coordinates; no automatic-position claim is supported.

## Caveats / Not Found

- The deployed host's exact source commit/package version remains unverified;
  matching a permissive MCP schema does not prove its parser/serializer body.
- Public wrapper source proves native serialization, not image quality,
  successful provider acceptance, focal behavior or model availability on the
  configured account. No paid call was made.
- True automatic positioning is not reachable through the reviewed
  `generate_image` signatures; omission of coordinates centers every item and
  activates the coordinate flag. Do not describe this as automatic placement.
- No verified official hard count limit was found. Six is the chosen workspace
  bound. Twenty-two is only a current documentation test claim for V5.
- Upstream returns only the **first** image block while saving paths for every
  image (`tools/generate.py` v0.4.0 L33–43; current L47–56). Existing workspace
  multi-sample behavior is a separate known integration uncertainty; this
  research does not change it or authorize following server-side paths.
