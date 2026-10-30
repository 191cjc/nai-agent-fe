# Character Dataset Runs, Reference Images and Trait Advice

## Scope / Trigger

Use when changing reference images, character dataset runs (vibe transfer /
image-to-image), style pools, character captions or trait advice. Character
runs are dataset runs (`kind: "dataset"`) and inherit every rule in
[Dataset Runs and Export](./dataset-run-contract.md) and
[Durable Experiments](./durable-experiment-contract.md).

## Signatures

- Schema 6 (`0006_reference_images.sql`): `reference_images(user_id, id,
  sha256, mime_type, width, height, byte_size, source, created_at)`.
  Bytes live in `<sqlite dir>/reference-images/<user_id>/<id>` (dirs 0700,
  files 0600), never in SQLite, logs or web root, and are not swept by the
  seven-day result cleaner.
- `GET /api/reference-images`; `POST /api/reference-images` (raw body,
  `Content-Type: image/png|image/jpeg`, ≤ 8 MiB, 415/413/422/409);
  `POST /api/reference-images/from-result {job_id, image_index}`;
  `GET /api/reference-images/{id}/image`; `DELETE /api/reference-images/{id}`
  (409 `reference_in_use` while a running/stopping run references it).
- `POST /api/reference-images/trait-advice {reference_ids (1..4), traits}`
  → `{suggestion}`; same errors as `/api/advice` plus
  `422 reference_not_found` and `502 advice_image_unsupported`.
- `POST /api/dataset-runs` optional `styles: [str] (1..8)` (first must equal
  `parameters.style_prompt`) and `character: {traits, mode: vibe|img2img,
  reference_ids (1..4), strength?, noise?}`. The response/definition stores
  `character.references: [{id, sha256}]` pinned at creation.
- `GenerationRequest.reference: {mode, images: [{id, sha256}], strength?,
  noise?}` exists only on run groups; ordinary `POST /api/generations`
  rejects it (422).

## Contracts

- Header-only validation (no image decoder dependency): PNG signature+IHDR
  or JPEG SOFn; sides 64..2048. Quota per owner: 20 images / 128 MiB, checked
  in the insert transaction; the file is removed if the insert fails.
- Group N: `style = styles[(N−1) mod S]` (or the frozen style),
  `positive = traits.strip() + ", " + item.prompt.strip()`,
  seed `base + N − 1`. Vibe: all references, model must be V4/V4.5 (V5
  rejects vibe upstream). Img2img: reference `[(N−1) mod R]`, strength
  0.01–0.99, noise 0–0.99, `extra_noise_seed = seed`; no native characters.
- Vibe on V4/V4.5 is two-step: each reference is first encoded with MCP
  `encode_vibe {reference, information_extracted, model}` and the returned
  token (not raw image base64) goes into `generate_image.references`. Raw
  images make NovelAI fail with "stream error: Internal Server Error"
  (verified 2026-10-29, PNG and JPEG). `information_extracted` (0.01–1.0,
  default 1.0) is frozen per run. Tokens are cached privately per owner under
  `reference-images/<user>/vibes/` keyed by sha256 + model + information and
  removed with the last copy of the image; encoding is a paid call and runs
  after the request snapshot is recorded. Missing `encode_vibe` →
  `unsupported_reference_mode` before any paid call.
- Upstream history: MCP `novelai-image` 4.0.0b3 initially returned HTTP 500
  for every vibe generation; after the service fix (2026-10-29) the same
  encode → token → `generate_image.references` flow succeeded (V4.5, one image
  ~65 s). The service now also accepts optional `reference_strengths` /
  `reference_information` (0.01–1.0, default 1.0, one per reference). The
  run's `reference_strength` (vibe only) is sent as `reference_strengths`
  (one value per reference); if the service lacks that field the group fails
  `unsupported_reference_mode` before any paid encode or generation. Image-to-image works (~132 s for one image) and
  uses a 600 s deadline.
- GPT image mode (`mode: "gpt"`, optional `gpt_quality` low|medium|high) is
  independent of NovelAI: enabled only with `NAI_GPT_IMAGE_API_KEY`
  (`GET /api/capabilities`; create → 503 `gpt_image_unavailable` otherwise),
  base URL `NAI_GPT_IMAGE_BASE_URL` or the advice relay, model
  `NAI_GPT_IMAGE_MODEL` (default `gpt-image-2.5-flare`). Each group is one
  multipart `POST {base}/images/edits` with every pinned reference as
  `image[]`, the deterministic prompt from `gpt_images.gpt_prompt` (traits,
  item, style), `size` ∈ 1024×1024 / 1024×1536 / 1536×1024, `n` 1–4. GPT groups
  pin neutral NAI fields (`sampler="gpt-image"`, steps 1, CFG 0, no quality,
  no negative) and are never sent to the NovelAI provider. 400 with
  moderation/safety wording → `content_policy`; transport failures after send
  → `outcome_unknown` (never retried). Verified with paid probes 2026-10-30
  (~90–116 s per image, ~3 MB PNG).
- Upstream tool errors are logged as one bounded, printable line
  (`NovelAI tool <name> failed: …`); they never contain images or tokens.
- At call time the manager loads bytes and verifies the pinned sha256;
  missing/changed → that group fails `reference_unavailable`, run continues.
- The provider checks `tools/list` for `references` / `image_to_image`
  fields before the paid call (`unsupported_reference_mode`), and records the
  request snapshot with `{sha256, byte_size}` in place of every base64 image.
- Captions: dataset item text only; trait tags (prefix of `positive_prompt`
  before the item) are removed even if repeated in the item; never style.
- Trait advice attaches the owner's chosen images as SDK `local_image`
  inputs (CLI `--image`) inside the isolated turn directory; tools stay
  disabled; 90 s timeout; dedicated identity-tag instructions. Each click is
  one paid call; the UI states images go to the configured advice provider.
- Legacy dataset/style definitions (no `styles`/`character`) are unchanged.
- The web style pool offers built-in presets (`apps/web/src/style-presets.ts`):
  eight medium/technique tag sets (all in colour: no monochrome/greyscale preset,
  since captions omit style and grey samples teach faded character colours), never artist tags, optionally prefixed with
  a user-entered prefix that is empty by default (quality tags only). Never
  prefix the draft style: it is itself a style and mixes into every preset.
  Entries are ordinary editable pool items (overwrite asks to confirm; append
  caps at 8). No server change.

## Tests Required

Fakes/MockTransport only (`tests/test_character_runs.py`, `test_advice.py`):
header validation, private modes, quota, owner isolation, in-use delete,
definition validation matrix, vibe/img2img arguments and redacted snapshots,
style/reference rotation, changed bytes failing one group, API upload/pick/
list/bytes/delete/trait advice, ordinary-generation rejection, legacy
definitions, migration v5→v6. Image-input support of the real advice model
needs one operator-approved probe.
