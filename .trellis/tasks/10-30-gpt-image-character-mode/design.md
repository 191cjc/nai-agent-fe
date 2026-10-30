# Design: GPT image character dataset mode

## Representation

A GPT group is still a character dataset group (same run table, scheduler,
job history, result store, viewer, export). To avoid a parallel request
model, it reuses `GenerationRequest` with:

- `reference.mode = "gpt"`, `reference.images` = all selected references
  (1–4, pinned sha256), `reference.gpt_quality` ∈ {auto, low, medium, high}.
- `model` = configured GPT model id (frozen), `width`/`height` ∈
  {1024×1024, 1024×1536, 1536×1024}; NAI-only fields carry fixed neutral
  values (`sampler="gpt-image"`, `steps=1`, `cfg_scale=0`, `quality=false`,
  `negative_prompt=""`, no characters) and are ignored by the GPT provider.
  Validators enforce these values for mode `gpt` so NAI settings can never
  leak in ("completely separate from NovelAI").
- Trade-off: one request model and all existing lifecycle code, at the cost
  of placeholder NAI fields on GPT rows.

## Prompt template (provider side, frozen inputs)

```
Use the attached reference image(s); they all show the same character.
Draw exactly this character: keep the face, hair, eyes, outfit, accessories
and weapon identical to the references.
Character: {traits}
Scene and pose: {item tags}
Art style: {style}
One character only. No text, no watermark, no signature.
```
`{traits}` / `{item}` / `{style}` come from the frozen group; the browser
shows a read-only preview for the first item before Start.

## Provider (`gpt_images.py`)

- `GptImageProvider(base_url, api_key, model)`; `POST {base}/images/edits`
  as multipart (`image[]` per reference, `prompt`, `model`, `size`, `n`,
  `quality` when not auto, `output_format=png`) using httpx (no new
  dependency). Response `data[].b64_json` → PNG bytes (size/format checked
  like NAI results, ≤ 8 MiB each).
- Status mapping: 401/403 → `provider_auth_error`; 429 →
  `provider_rate_limited`; 400 with moderation/safety/policy wording →
  `content_policy`; other 4xx → `invalid_request`; 5xx/timeout/transport
  after send → `outcome_unknown` (never retried). Bounded body reading
  (`_http_response`), 600 s deadline. Upstream error text logged as one
  bounded printable line (never the key or images).
- `record_request` snapshot: model, size, n, quality, prompt, and
  `{sha256, byte_size}` per reference — no base64, no key.

## Backend wiring

- `Settings`: `gpt_image_api_key` (secret, repr=False), `gpt_image_base_url`
  (validated like the Codex base URL; default = Codex base URL), and
  `gpt_image_model` (default `gpt-image-2.5-flare`).
- `GenerationManager` gets an optional `gpt_provider`; `_run` dispatches
  mode `gpt` to it (reference bytes loaded/verified exactly as today).
- `POST /api/dataset-runs` with mode `gpt` → `503 gpt_image_unavailable` when
  unconfigured; `GET /api/capabilities` (or a field on an existing session/
  health response) tells the web whether the mode is available.
- `CharacterRequest.mode` gains `"gpt"` + `gpt_quality`; style pool and
  item rotation unchanged; captions unchanged.

## Frontend

- Character mode radio gains 「GPT 参考图生成」 (disabled with notice when
  unavailable). In this mode NAI model/size/steps/sampler/negative inputs are
  replaced by: output size (竖 1024×1536 / 方 1024×1024 / 横 1536×1024),
  quality, images per item (1–4). Prompt preview of item 1. Notice: images
  and prompts go to the relay's GPT model; refusals possible; cost per image.

## Verification

- MockTransport tests: multipart fields, prompt template, size/quality,
  snapshot redaction, status/refusal mapping, unconfigured 503, manager
  dispatch never touching the NAI provider.
- Paid probes (operator-approved budget): 1 edits call with one reference
  to confirm field names/response; adjust before shipping.

## Rollout

API (no schema change) then web. Operator adds `NAI_GPT_IMAGE_API_KEY`
privately via `sudoedit /etc/novelai/api.env` and restarts when idle.
