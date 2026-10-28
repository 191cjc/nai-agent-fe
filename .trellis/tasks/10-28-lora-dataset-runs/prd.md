# LoRA training dataset batch runs

## Goal

Let a user produce a style-LoRA training set with this workspace: pick content
prompts from a built-in standard training prompt library, run them all as one
durable server batch under the current draft's fixed style section, then
export clean images with matching caption files. Separately, let a user pack
selected ordinary history images into the same dataset format.

## Confirmed Decisions (operator, 2026-10-28)

- Prompt source: a **built-in curated library** shipped with the web app. No
  AI/Codex generation, no paid call to build the list. Reviewable and stable.
- Selection: check whole categories, then uncheck/edit/remove individual
  items and add custom items. Before Start show item count × images per item
  = total images.
- Characters: dataset prompts live entirely in the shared (`公共`) content as
  generic tags (`1girl`, `1boy`, `2girls` …). No native character cards in
  dataset runs, so any supported model works. The style comes from the
  current draft's `画风` section, frozen at Start.
- Packing selected history images is also in scope ("打包是一方面").

## Requirements

### R1 Built-in training prompt library
- About 100–150 English Danbooru-tag content prompts, grouped in categories
  that cover style-LoRA diversity: shot/framing (portrait, upper body, cowboy
  shot, full body), pose/action, setting (indoor, outdoor, urban, nature,
  fantasy), lighting/time of day, subject count/gender, objects/animals/
  scenery without people.
- Content only: no artist/style/medium/quality tags inside library prompts,
  so captions describe content and the LoRA absorbs the style.
- Each item has a stable id, category and prompt text; categories have
  Chinese labels.

### R2 Dataset run configuration UI
- Opened from the workspace next to the style experiment entry.
- Category checkboxes with counts; per-item checkbox, inline edit, remove;
  "add custom prompt"; reset to library defaults.
- Uses the current draft's style section, negative prompt, model, size,
  steps, CFG, sampler, quality and images-per-item (sample_count). Shows the
  frozen style text that will be applied.
- Shows total groups/images before Start. Start requires explicit click and
  issues exactly one create request.
- Validation before POST: at least 1 item, at most 300 items; each item
  non-empty, within prompt limits when combined with the style; no item may
  begin a line with `//` (comment syntax).

### R3 Durable dataset run (server)
- Same durability guarantees as style experiments: server-owned, survives
  browser close/refresh/logout, failed items recorded and skipped, explicit
  Stop only, no automatic retry of any paid group, lost create response
  reconciled by known-id GET only.
- Each item uses a **different deterministic seed**: base seed (user-given or
  random once) + item ordinal − 1, wrapped into the valid seed range. The base
  seed is shown.
- At most one active run per owner across style and dataset runs (shared
  limit); the existing active-run check/reattach also finds dataset runs.
- Every group is saved as ordinary history with run metadata identifying the
  run, ordinal and item id/text, viewable with the existing saved-results
  viewer (left/right navigation, placeholders for failed/expired groups).

### R4 Dataset export (zip)
- Export from (a) a dataset run's saved groups, (b) a user selection of
  ordinary history items.
- Zip contains `NNNN.png` + `NNNN.txt` pairs. Images go through the existing
  clean export (no PNG text chunks, stealth LSB carriers cleared).
- Caption = optional trigger word, then the content prompt that was actually
  used, excluding the style section: for dataset runs the frozen item text;
  for history items the effective shared prompt plus effective character
  prompts (hidden/comment lines removed). Whitespace/comma normalized.
- Trigger word is entered at export time (optional).
- Expired/failed groups are skipped and counted in a visible summary. The zip
  contains only images and captions.
- Export reads images one at a time from the authenticated image endpoint;
  it never triggers generation. Cancelable.

## Constraints

- Paid operations: Start is the only paid action; nothing auto-resubmits.
  Tests use fakes only; no paid probes.
- Images are retained for 7 days; UI states this near export.
- No new backend or frontend dependencies. Operator restriction: no frontend
  automated tests/browser automation; ESLint/TypeScript/build + source review.
- Backward compatible with stored style runs and history; existing
  style-experiment API responses keep their shape (new fields are additive).
- Depends on the uncommitted `provider_request` work on this branch being
  committed first (schema version 5); this task's migration (if any) follows it.

## Acceptance Criteria

- [ ] Library of ≥100 content-only prompts across ≥6 categories, visible and
      selectable by category and item; custom items addable/editable.
- [ ] Start creates one durable dataset run; closing the page does not stop
      it; re-entry reattaches; Stop prevents later items.
- [ ] Each item's saved history row has a distinct seed = base + ordinal − 1
      (wrapped) and the frozen style + item prompt; failures continue.
- [ ] Style and dataset runs cannot both be active for one owner.
- [ ] Existing style experiment create/run/view behavior unchanged
      (backend regression tests pass).
- [ ] Export of a dataset run and of selected history produces a zip of clean
      PNGs and matching captions without style text; trigger word prepended
      when given; skipped items reported.
- [ ] Backend: ruff + pytest (fakes only) incl. new dataset-run tests;
      OpenAPI contract regenerated and reviewed. Web: lint + tsc + build.

## Out of Scope

- AI-generated or AI-expanded prompt lists.
- Native character cards / coordinates in dataset runs.
- Training the LoRA, cropping/bucketing, tag auto-captioning of images.
- Server-side zip creation or long-term image retention changes.
