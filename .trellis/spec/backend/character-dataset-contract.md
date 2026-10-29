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
  eight medium/technique tag sets, never artist tags, optionally prefixed with
  the draft style; they are ordinary editable pool entries (overwrite asks to
  confirm; append caps at 8). No server change.

## Tests Required

Fakes/MockTransport only (`tests/test_character_runs.py`, `test_advice.py`):
header validation, private modes, quota, owner isolation, in-use delete,
definition validation matrix, vibe/img2img arguments and redacted snapshots,
style/reference rotation, changed bytes failing one group, API upload/pick/
list/bytes/delete/trait advice, ordinary-generation rejection, legacy
definitions, migration v5→v6. Image-input support of the real advice model
needs one operator-approved probe.
