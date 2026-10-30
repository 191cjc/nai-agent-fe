# Fixed-style Dataset Runs and Training-set Export

## Scope / Trigger

Use when changing dataset (LoRA training set) runs, the built-in training
prompt library, dataset group metadata, or the browser zip export. A dataset
run is a second kind of the [Durable Experiments](./durable-experiment-contract.md)
run and inherits every lifecycle guarantee there (single create POST, known-id
reconciliation, failure continuation, explicit Stop, no paid retry, restart
reconciliation, one active run per owner). Frontend lifecycle rules follow
[Style Experiment Contract](../frontend/style-experiment-contract.md).

Character runs (reference images, style pools, traits) extend this contract;
see [Character Dataset Runs](./character-dataset-contract.md).

## Signatures

- `POST /api/dataset-runs`: `{id: UUID, parameters: GenerationRequest,
  items: [{id, prompt}]}` -> 202 `RunState` with `kind: "dataset"`,
  `items`, `ranges: []`. Same 401/403/409/422/503 mapping as style runs.
- Reads and Stop reuse `GET /api/style-experiment-runs/active`,
  `GET /api/style-experiment-runs/{id}`, `POST …/{id}/stop`.
  `RunState.kind` defaults to `"style"`; `items` defaults to `[]` (additive).
- `ExperimentContext` (in `settings_json.experiment`): style groups omit
  `kind`/`item` and require 1..1500 weights; dataset groups have
  `kind: "dataset"`, one `item`, `weights: []`.
- `ExperimentSummary.kind` is `"style" | "dataset"` derived from stored rows.
- No schema migration: run `definition_json` gains `{"kind": "dataset",
  "parameters", "items"}`; absent kind means a style definition.

## Contracts

- Request parameters carry only style + settings: `positive_prompt == ""`,
  no characters, no `prompt_sections`, no `experiment`; effective style must
  be non-blank. Items: 1..300, unique ids `^[a-z0-9][a-z0-9-]*$` (≤64),
  non-blank prompt ≤1000 chars, no `//` comment line when `prompt_comments`,
  and every item must validate as a full `GenerationRequest` (combined
  style + item ≤3000).
- Ordinal N renders `positive_prompt = items[N-1].prompt` and seed
  `(base - 1 + N - 1) % 4294967295 + 1`, where base is the persisted run
  seed (request seed or random once). Seeds intentionally vary per item.
- Dataset and style runs share the one-active-run index; a dataset id that
  collides with a style run id conflicts (`experiment_run_conflict`).
- Ordinary `POST /api/generations` cannot carry dataset metadata
  (409 `experiment_conflict`); dataset groups exist only as run claims.
- Export runs in the browser, reading retained images one at a time through
  `sanitizedPng` (no PNG text chunks, cleared LSB carriers) into an
  uncompressed zip of `NNNN.png` + `NNNN.txt`. Captions never include style:
  dataset groups use the frozen item prompt; ordinary history uses effective
  shared + character prompts. NovelAI emphasis syntax is stripped, tags are
  comma-normalized and de-duplicated, and an optional trigger word leads.
  Export never generates; failed/expired images are counted as skipped.
- The library (`apps/web/src/dataset-prompts.ts`) contains content-only
  Danbooru tags: no artist, medium, style or quality tags.

## Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Shared/character/sections content in run parameters | 422, no state |
| Blank or comment-only style | 422 |
| 0 or >300 items, duplicate/invalid id, blank/comment/over-limit item | 422 |
| Another active style or dataset run | 409 `experiment_run_active` |
| Ordinary generation with dataset context | 409 `experiment_conflict` |
| Item group fails | Counted failed, next item continues, no retry |
| Image expired/unavailable during export | Skipped and reported; zip continues |
| 401 or cancel during export | Export aborts; no partial download |

## Tests Required

Fakes only (`tests/test_dataset_runs.py`): validation matrix, seed wrap,
frozen style/item at the fake provider, failure continuation, Stop and
restart without repeated items, idempotency/conflict, shared active limit,
API create/reattach/owner isolation/Origin, summary kind, ordinary
injection refusal. Frontend: lint, TypeScript, env-free build and source
review only (operator restriction); no paid probes.

## Wrong vs Correct

- Wrong: reuse one fixed seed for every dataset item, or include the style
  section in captions (the LoRA then binds style to the caption text).
- Correct: vary seeds deterministically, keep captions content-only, and
  let the shared durable scheduler own every paid item.

## Review: discard marks and multi-set export (schema 7)

- `PUT/DELETE /api/generations/{job_id}/images/{image_index}/discard` mark or
  restore one image of the owner's succeeded job (idempotent, Origin-checked,
  404 for foreign/missing jobs or indexes ≥ image_count). Marks live in
  `discarded_images(user_id, job_id, image_index)` and cascade with the job;
  image files are never deleted by a mark.
- `GenerationView.discarded_images` (sorted indexes) is present on every
  view; experiment pages batch the lookup (`GenerationManager.views`).
- The viewer shows an 「已弃置」 badge, 「弃置」/「恢复」 and a 「只看未弃置」 toggle
  that keeps stepping in the same direction past discarded images.
- Every export (one set, several sets merged, selected history) re-reads
  groups at export time and skips discarded images, counting them separately
  from failed/expired ones; numbering stays contiguous across merged sets.
- Export captions may carry an optional user prefix (UI preset for Animagine
  XL 4.0: `masterpiece, high score, great score, absurdres`): order is trigger,
  prefix tags, then content tags, de-duplicated. Empty prefix keeps the
  previous captions exactly. Only quality tags belong there; texture/style
  features the LoRA should learn (skin gloss, eye detail) stay out of
  captions so they bind to the LoRA itself.

