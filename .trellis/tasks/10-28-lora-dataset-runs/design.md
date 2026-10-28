# Design: LoRA training dataset batch runs

## Overview

A dataset run is a second kind of the existing durable style-experiment run.
It reuses the run table, scheduler, claim/reconcile, Stop, one-active-run
index, reattach flow and saved-results viewer. Only plan derivation differs:
instead of a Cartesian weight grid over the style, ordinal N renders the
frozen style with item N's content prompt and seed `base + N − 1`.

No schema migration: `style_experiment_runs.definition_json` and the job's
`settings_json.experiment` are JSON and absorb the new fields additively.

## Backend

### Models (`generations.py`)
- `DatasetItem {id: str(1..64, [a-z0-9-]), prompt: str(1..1000)}`.
- `ExperimentContext` gains `kind: Literal["dataset"] | None` (excluded when
  None) and `item: DatasetItem | None` (excluded when None).
  Validator: style contexts (kind None) keep `weights` 1..1500 and no item;
  dataset contexts require `item` and `weights == []`. Old rows validate
  unchanged, so `valid_experiment()` and `EXPERIMENT_ROWS` keep working.
- `ExperimentSummary.kind: Literal["style", "dataset"]` derived in SQL from
  `json_extract(settings_json, '$.experiment.kind')` (NULL → style). Additive.

### Run definition (`style_experiments.py`, new `dataset_plan.py`)
- `DatasetRunCreate {id: UUID, parameters: GenerationRequest,
  items: list[DatasetItem] (1..300, unique ids)}`. Rules on `parameters`:
  `experiment` None, `positive_prompt == ""`, `character_prompts == []`,
  `prompt_sections` None. Per item: non-blank; when `prompt_comments`, no line
  may start with `//`; `len(effective_style) + 2 + len(item) <= 3000`.
- `definition_json = {"kind": "dataset", "parameters": …, "items": […]}`;
  `total = len(items)`. Style definitions keep their current JSON exactly
  (absent kind = style) so same-id idempotency/conflict comparison of old
  runs is untouched.
- `RunStore.create` is generalized to accept either create model; the
  existing same-owner/id compare, active check (`experiment_run_active`) and
  used-id check apply to both. A dataset id colliding with a style run id is
  a conflict.
- `RunState` gains `kind: Literal["style","dataset"] = "style"` and
  `items: list[DatasetItem] = []`; `ranges` is `[]` for dataset runs.
- `group_parameters(run)` dispatches on kind. Dataset branch:
  `positive_prompt = item.prompt`, `seed = (run.seed - 1 + ordinal - 1) %
  4294967295 + 1`, `experiment = ExperimentContext(kind="dataset", item=item,
  weights=[], id, ordinal, total)`. Everything else is the frozen snapshot.
- Scheduler (`StyleExperimentService`) is unchanged apart from calling the
  dispatching `group_parameters`.

### API (`app.py`)
- New `POST /api/dataset-runs` → 202 `RunState` (same auth, Origin, 409/422
  mapping as `create_style_run`).
- Reuse `GET /api/style-experiment-runs/active`, `GET …/{id}`,
  `POST …/{id}/stop` for both kinds (they already key only by owner/id).
- `GET /api/style-experiments[/{id}]` lists/returns dataset runs too, with
  `summary.kind`, items carrying `parameters.experiment.item`.
- Regenerate `contracts/openapi.json`; update `test_api_contract.py`.

## Frontend

### Library — `dataset-prompts.ts`
Static `DATASET_CATEGORIES: {id, label}[]` and `DATASET_PROMPTS:
{id, category, prompt}[]` (~120 items, content-only Danbooru tags). Items
are authored to vary framing, pose, setting, lighting and subject count
independently, and include ~10 no-human scenery/object prompts.

### Selection model — `dataset-run.ts`
Pure helpers: default selection, toggle category/item, edit/remove/add custom
(`custom-<n>` ids), and `validateDatasetItems(items, draft)` mirroring the
server rules. `datasetRunParameters(draft)` builds the frozen request
parameters from the current draft (style + negative + settings, empty shared,
no characters/sections).

### Run lifecycle — `style-run-store.ts`
Extend the existing store (it already owns active-run check, create
reconciliation by known UUID, polling, Stop, session epochs) with
`startDataset(items)`, sharing every safeguard. `RunState.kind` selects the
progress labels ("条目" vs "组合").

### UI — `DatasetRun.tsx`
Panel opened next to the style experiment entry: frozen style preview,
category checkboxes with counts, item list (checkbox, inline edit, delete),
add custom, reset, total items × images, base seed field, Start/Stop and
progress (reusing StyleExperiment progress markup where practical).

### Export — `dataset-export.ts` + UI hooks
- Minimal STORE (uncompressed) zip writer with CRC-32, built as a `Blob`
  from parts; no dependency. Filenames `0001.png`/`0001.txt`.
- Images: for each succeeded job image, fetch the authenticated PNG, create a
  temporary Blob URL, run existing `sanitizedPng`, revoke. Sequential,
  cancelable via `AbortSignal`, progress reported.
- `datasetCaption(job, trigger)`: dataset item → `item.prompt`; ordinary
  history → effective shared + effective character prompts (comments compiled
  out, style excluded); normalize comma/whitespace; prepend trigger if set.
- Entry points: "导出训练集" on a dataset experiment in SavedResults (all its
  groups, paged through the detail endpoint) and a selection mode on the
  history list ("选择 → 导出训练集"). Trigger word input + skipped summary.

## Compatibility / Rollout

- Additive API fields; old web clients ignore `kind`/`items`. Old API +
  new web: dataset POST 404 → shown as safe error; deploy API first as usual.
- No migration; rollback = redeploy previous build. Dataset runs left in the
  DB would fail to parse under an old API → stop/complete active dataset runs
  before rolling back (documented in deployment notes).

## Trade-offs

- Reusing `/api/style-experiment-runs/*` for both kinds avoids a parallel
  lifecycle at the cost of a slightly style-specific path name.
- Shared one-active-run limit is simpler and protects the single paid worker;
  users cannot run a style sweep and a dataset run simultaneously.
- Client-side zip keeps sanitization in the one place it already exists, but
  a large export holds image Blobs in the browser (≈300 × ~1.5 MB worst case).
