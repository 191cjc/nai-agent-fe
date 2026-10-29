# Character LoRA dataset runs

## Goal

Let a user build a training set for a character LoRA: start from one or more
reference images of a character, batch-generate the character in many poses,
framings, expressions and settings through NovelAI, curate the results, and
export clean images with character-aware captions. Builds on the existing
style-LoRA dataset runs (`10-28-lora-dataset-runs`, `dataset-run-contract.md`).

## Confirmed Facts (repository / upstream evidence, 2026-10-29)

- Upstream MCP `novelai-image` 4.0.0b3 (non-billable `tools/list`):
  - `generate_image.references`: list of base64 PNG/JPEG → vibe transfer.
    **V4/V4.5 only; V5 rejects it.** No per-reference strength / information
    extracted parameter is exposed.
  - `image_to_image`: required `prompt`, `image` (base64 PNG/JPEG);
    `strength` 0.01–0.99 (default 0.3), `noise` 0–0.99 (default 0),
    `extra_noise_seed`; same model/size/steps/scale/sampler/seed/n_samples/
    quality fields; **no `character_prompts`**. "Model must match the input
    image domain."
  - No precise "character reference" parameter is exposed.
- Current adapter (`mcp_images.py`) only calls `generate_image` with text
  fields and persists the exact provider arguments (`provider_request_json`)
  before the paid call — base64 image payloads must not be stored there.
- Dataset runs already provide: durable server run, per-item seeds
  (base + N − 1), failure continuation, Stop, one active run per owner,
  saved-result viewing and browser zip export with clean PNGs.
- Existing built-in prompt library mixes `1girl`/`1boy`, multi-person,
  no-human and appearance tags (hair colour etc.) — unsuitable as-is for a
  single character whose appearance is fixed.

## Confirmed Decisions (operator, 2026-10-29)

- Q1 Both modes, chosen per run: **vibe transfer** (V4/V4.5 models only) or
  **image-to-image** (any listed model; strength/noise set per run).
- Q2 Reference source: **local upload** and **pick from saved history images**
  (copied server-side, no re-upload).
- Q3 **Up to 4 reference images** per run: vibe uses all of them together on
  every item; image-to-image rotates them across items
  (item N uses image `(N − 1) mod count`).
- Q4 **Optional style pool**: 1–8 style prompts rotated across items
  (item N uses style `(N − 1) mod count`); one entry = fixed style.

## Requirements

### R1 Reference images
- Upload PNG/JPEG (≤ 8 MiB, ≤ 2048×2048 decoded size, format verified by
  signature/header) or copy a retained history result image.
- Stored privately per owner on disk (not SQLite, not web root, not logs),
  metadata in SQLite; listed, previewed and deletable by the owner. Bounded
  per owner (≤ 20 images, ≤ 128 MiB). Kept until deleted (not 7-day expiry);
  deletion is refused while an active run uses the image.
- Provider-request snapshots record only image digest/size, never base64.

### R2 Character definition
- Character trait tags (e.g. `1girl, solo, silver hair, red eyes, black
  hoodie`): included in every prompt, excluded from captions.
- Built-in character content library (~100 items): framing/angle,
  expression, pose/action, setting, lighting, and an optional outfit-variation
  category (unchecked by default). No gender/count/appearance tags. Same
  category/item selection, editing and custom items as the style library.

### R3 Character dataset run
- Prompt for item N = style[(N−1) mod S] + traits + item N content.
- Mode vibe: `generate_image` with all references; model must be V4/V4.5.
  Mode img2img: `image_to_image` with reference[(N−1) mod R], strength
  (0.01–0.99, default 0.55) and noise (0–0.99, default 0); no native
  character cards in either mode.
- Seeds: base + N − 1 (as dataset runs). Durable lifecycle, Stop, failure
  continuation, no retry, shared one-active-run limit — unchanged.
- Before Start show items × images, mode, model compatibility and that each
  item is one paid generation (vibe/img2img may cost more Anlas).

### R4 Captions and export
- Character caption = trigger word + item content tags; never style, never
  trait tags (also strips any trait tag that appears in item text).
- Export reuses the dataset zip (clean PNG + .txt). Viewer shows mode,
  reference thumbnails and style used per item to support manual curation;
  export can exclude items the user marked as rejected.

### R5 AI trait suggestion from reference images (operator, 2026-10-29)
- In the character panel, a 「根据参考图建议角色特征」 action sends the
  selected reference images (1–4) plus the current trait text to the existing
  AI advice service and returns suggested trait tags.
- Suggestion: English Danbooru-style comma-separated tags for persistent
  identity only — subject count/gender, hair (colour/length/style), eyes,
  distinctive features (marks, accessories, ears/tail…), default outfit.
  Excludes pose, expression, framing, background, lighting, style/medium and
  quality tags. Revises the current traits (keeps correct ones, fixes wrong
  ones) rather than ignoring them.
- Shown as editable plain text with explicit 「替换」/「追加」; never applied
  automatically. Explicit click only; each click is one paid advice call.
- Images go only to the configured advice provider as user-message
  attachments of that single turn (UI states this); no tools enabled; nothing
  persisted besides the existing reference images.
- Unverified: whether the configured advice model accepts images. One
  operator-approved real probe is required during implementation; if
  unsupported, the action reports a clear "model does not support images"
  error and the rest of the feature is unaffected.

## Acceptance Criteria

- [ ] Upload and history-pick both create owner-private reference images;
      invalid/oversize/foreign/over-quota inputs are refused; deletion blocked
      while an active run uses them.
- [ ] Vibe runs send all references to `generate_image`; img2img runs send the
      rotated reference with strength/noise to `image_to_image`; V5 + vibe is
      refused before Start (UI) and at create (422).
- [ ] Style pool and reference rotation follow the ordinal formulas;
      seeds are base + N − 1; frozen definition ignores later draft edits.
- [ ] No base64 image bytes in SQLite, provider-request snapshots or logs.
- [ ] Captions contain trigger + content only (no style, no traits).
- [ ] Trait advice sends only the chosen owner reference images + current
      traits; suggestion is editable and applied only by explicit replace/
      append; failures (busy, timeout, image unsupported) leave traits intact;
      fake-runner tests cover image attachment, isolation and cleanup.
- [ ] Existing style/dataset runs, ordinary generation and history unchanged;
      migration v5→v6 preserves data; fake-only backend tests; web lint/tsc/
      env-free build; no paid probes (schema `tools/list` probes allowed).

## Out of Scope (proposed)

- LoRA training itself, auto-tagging/cropping, face-similarity scoring.
- Inpaint/upscale steps in the run.
- Reference images for ordinary (non-run) generation.
- Per-reference vibe strength / information-extracted controls (not exposed
  by the upstream tool).
