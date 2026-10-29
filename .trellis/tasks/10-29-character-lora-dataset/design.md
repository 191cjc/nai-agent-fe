# Design: Character LoRA dataset runs

## Overview

A character run is a dataset run (`kind: "dataset"`) with an optional
`character` block and an optional style pool. It reuses the durable run
table, scheduler, Stop, reattach, saved viewer and zip export. New pieces:
a private reference-image store, provider support for vibe references and
`image_to_image`, a character prompt library and character-aware captions.

## Data and storage

### Migration `0006_reference_images.sql` (schema 6)
```
reference_images(
  user_id TEXT NOT NULL REFERENCES users(id),
  id TEXT NOT NULL,              -- UUID
  sha256 TEXT NOT NULL,
  mime_type TEXT NOT NULL CHECK (mime_type IN ('image/png','image/jpeg')),
  width INTEGER NOT NULL, height INTEGER NOT NULL, byte_size INTEGER NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('upload','result')),
  created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, id))
```
Additive; v5 data untouched. Backup/restore and deployment notes updated.

### `ReferenceImageStore` (new `reference_images.py`)
- Files under `<sqlite dir>/reference-images/<user_id>/<id>` (dirs 0700,
  files 0600, `O_NOFOLLOW`, same safe-open helpers as `DiskResultStore`).
  Not swept by the 7-day result cleaner; removed only on owner delete.
- Validation without new dependencies: PNG signature + IHDR, or JPEG
  SOI + SOFn marker for dimensions; ≤ 8 MiB, each side 64..2048.
- Quota per owner: ≤ 20 images and ≤ 128 MiB, checked in the insert
  transaction. Deletion refused (`409 reference_in_use`) when any
  running/stopping run definition references the id.
- Copy from history: read retained result bytes via `ResultCache.image`
  (owner-checked, unexpired) and store as `source='result'`.

### API (all owner-scoped, Origin-checked mutations, `no-store`)
- `POST /api/reference-images` — raw body, `Content-Type: image/png|jpeg`
  (no multipart dependency) → 201 `ReferenceImage` metadata.
- `POST /api/reference-images/from-result` `{job_id, image_index}` → 201.
- `GET /api/reference-images` → list; `GET /api/reference-images/{id}/image`
  → bytes (`nosniff`, `no-store`); `DELETE /api/reference-images/{id}` → 204.

## Run definition

`DatasetRunCreate` gains optional fields (absent = current style dataset run;
stored definitions unchanged):
```
styles: list[str] (1..8)          # style pool; replaces parameters.style_prompt per item
character: {
  traits: str (1..1000),          # fixed tags, in prompt, never in captions
  mode: "vibe" | "img2img",
  reference_ids: [UUID] (1..4),   # owner's reference images, frozen with sha256
  strength: float 0.01..0.99,     # img2img only
  noise: float 0..0.99            # img2img only
}
```
Rules: vibe requires a V4/V4.5 model (`NATIVE_CHARACTER_MODELS` minus V5);
references must exist for the owner at create; definition freezes each
reference's id + sha256 (a later replacement cannot change a frozen run).

Group for ordinal N (extends `group_parameters` dataset branch):
- `style_prompt = styles[(N−1) % S]` when a pool is present.
- `positive_prompt = traits + ", " + item.prompt` (bounded ≤ 3000 combined).
- `reference = ReferenceUse(mode, ids=[all] | [ids[(N−1) % R]], strength,
  noise, sha256s)` stored on the `GenerationRequest` (new optional field,
  excluded when None; ordinary POST rejects it with 422).
- `experiment.item` unchanged; context gains `traits` only via the run, and
  the caption uses `item.prompt` (traits never in item text).

## Provider (`mcp_images.py`)

- `tools/list` check per call: vibe → `generate_image.properties.references`
  must exist; img2img → `image_to_image` with `image`, `strength`, `noise`.
  Missing → `ProviderFailure("unsupported_reference_mode")` before paid call.
- Arguments: vibe adds `references: [base64…]`; img2img calls
  `image_to_image` with `image`, `strength`, `noise`, `extra_noise_seed=seed`
  and no character fields.
- Bytes are read from `ReferenceImageStore` at call time and verified against
  the frozen sha256 (`reference_changed` failure otherwise; group fails, run
  continues). `record_request` receives a copy where each base64 string is
  replaced by `{"sha256", "byte_size"}`.
- Request body size: ≤ 4 × 8 MiB × 4/3 base64 ≈ 43 MiB worst case; HTTPX
  timeout unchanged; uncertain outcome still never retried.

## Frontend

- `api.ts`: reference image types/methods; `GenerationRequest.reference`;
  `DatasetRunDefinition.styles/character`.
- `character-prompts.ts`: ~100 content-only items, categories
  framing/angle, expression, pose/action, setting, lighting, outfit
  (outfit unchecked by default). No gender/count/appearance tags.
- `DatasetRun.tsx`: mode switch 「画风训练集 / 角色训练集」. Character mode:
  reference picker (upload, list with thumbnails/delete, pick-from-history
  dialog), traits field, vibe/img2img switch with strength/noise inputs and
  model compatibility notice, style pool editor (add/remove up to 8, default
  = current draft style), character library selection, totals and Start.
- `SavedResults.tsx` viewer: show mode, used reference thumbnail(s), style
  and traits for dataset groups; history image actions get 「设为参考图」.
- Export: captions via `datasetCaption` (item prompt only; also strip any
  trait tag present); character runs offer a per-item include checklist in
  the export panel (client-side curation, nothing persisted).

## AI trait advice (R5)

- `POST /api/reference-images/trait-advice` `{reference_ids: [UUID] (1..4),
  traits: str (0..1000)}` → `AdviceResult`. Owner-checked ids; same auth,
  Origin, rate/capacity (`AdviceService` semaphore) and error codes as
  `/api/advice`, plus `422` for missing/foreign references.
- `CodexAdviceRunner.run(text, images=[...])`: copies the reference bytes into
  the isolated temp workspace (0600) and passes them as SDK
  `{"type": "local_image", "path": …}` inputs (CLI `--image`, a user-message
  attachment). `view_image`/all tools stay disabled; workspace and copies
  are removed after the turn. Dedicated instructions for identity traits
  (see PRD R5); output schema unchanged (`suggestion`).
- Timeout for image turns: 90 s (text advice stays 45 s).
- Image-unsupported upstream errors map to `502 advice_image_unsupported`
  when recognisable, otherwise `advice_failed`.
- Frontend: button + popover in the character panel reusing
  SectionAssistant patterns (explicit submit, stale-response discard on
  close/reference change, replace/append, safe errors).
- Spec: `codex-advice-contract.md` gains a scoped exception — attached owner
  reference images for this endpoint only; still no tool use and no claims
  about images the model was not given.

## Compatibility / rollout

- API first (migration 6 at `ExecStartPre`), then web. Old web ignores new
  fields. Rollback API below v6 requires restoring the pre-upgrade backup;
  keep new API on web rollback. Reference image directory needs separate
  private backup like generation images.
- Existing dataset/style definitions have no `styles`/`character` and render
  exactly as before (tests assert byte-identical group parameters).

## Trade-offs

- Raw-body upload avoids `python-multipart` at the cost of one file per
  request (fine for ≤ 4 images).
- Keeping `kind: "dataset"` reuses viewer/export/summary paths; the
  character block distinguishes behaviour without a new run kind.
- Client-side curation keeps the schema small; rejected marks are not
  remembered across page reloads.
