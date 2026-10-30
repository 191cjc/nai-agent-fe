# GPT image character dataset mode

## Goal

Add a third generation mode to character training sets: the relay's
`gpt-image-2.5-flare` model edits the selected reference image(s) into each
content prompt, aiming for better character consistency than NovelAI vibe /
image-to-image on complex designs. Batch durability, curation, export and
captions reuse the existing character dataset run.

## Confirmed Decisions (operator, 2026-10-30)

- Scope: **third generation mode of character training sets only** (not
  ordinary single generation).
- **Completely separate from NovelAI**: no NovelAI post-processing (no NAI
  image-to-image style conversion) and NovelAI settings (model, sampler,
  steps, CFG, NAI negative prompt, NAI quality) do not apply to this mode.
- The relay requires a **separate API key** for the image model.

## Confirmed Facts (2026-10-30)

- Relay `https://api.airoo.cc` exposes `POST /v1/images/generations` and
  `POST /v1/images/edits` (401 without key; unknown paths 404).
- Character runs already provide owner-private reference images, traits
  excluded from captions, style pool, durable batch, viewer, export with
  per-item curation (`character-dataset-contract.md`).
- Exact request/response fields of `gpt-image-2.5-flare` on this relay
  (sizes, quality, multiple input images, response format, refusals) are
  unverified and need operator-approved paid probes.

## Requirements

- R1 Configuration: new server secrets `NAI_GPT_IMAGE_API_KEY` (required to
  enable), optional `NAI_GPT_IMAGE_BASE_URL` (default: relay base) and
  `NAI_GPT_IMAGE_MODEL` (default `gpt-image-2.5-flare`), set privately in
  `/etc/novelai/api.env`; never in browser, logs, snapshots or tracked files.
  Mode is hidden/disabled with a clear notice when not configured.
- R2 Mode settings: selected references (1–4, all attached to every item),
  traits, style pool (natural-language or tag styles; presets reused), output
  size (portrait / square / landscape), quality (if supported), images per
  item. No NAI fields shown in this mode.
- R3 Prompt: deterministic English template per item: keep the exact
  character from the attached reference(s) (face, hair, eyes, outfit,
  accessories, weapon) + traits + item content + style; single character, no
  text/watermark. Template visible (read-only preview) before Start.
- R4 Durable batch identical to character runs: one paid call per item, no
  retry, failure continuation, Stop, one active run, frozen definition.
  Content-policy refusals are recorded as a distinct failure code and the run
  continues.
- R5 Results stored, viewed, curated and exported like other groups;
  captions = trigger + item tags (no traits, no style). Request snapshots
  never contain image bytes or the key.

## Acceptance Criteria

- [ ] Without the GPT key the mode is unavailable; with it, a run sends one
      edits request per item with all references and the composed prompt.
- [ ] Refusals, auth, rate-limit and timeout map to safe codes; uncertain
      outcomes are never retried; the run continues.
- [ ] NAI runs/settings unchanged; GPT groups never call the NAI provider.
- [ ] Fake-transport backend tests; web lint/tsc/env-free build; at most the
      operator-approved number of paid probes to confirm fields/format.

## Out of Scope

- Automatic NAI style conversion of GPT output.
- GPT for ordinary single generation or style training sets.
- Auto-tagging GPT images (captions come from item tags).
