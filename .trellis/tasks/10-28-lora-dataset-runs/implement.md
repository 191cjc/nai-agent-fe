# Implementation plan

Precondition: the uncommitted `provider_request` work on
`feat/native-character-prompts` is committed (or explicitly carried) first.

## Backend (apps/api)
1. `generations.py`: `DatasetItem`; `ExperimentContext.kind/item` + validator;
   `ExperimentSummary.kind` and SQL projection.
2. `dataset_plan.py`: `DatasetRunCreate` validation, definition JSON,
   dataset `group_parameters` branch, seed wrap helper.
3. `style_experiments.py`: generalize `RunStore.create`/`_state`
   (`kind`, `items`), dispatch in `group_parameters`.
4. `app.py`: `POST /api/dataset-runs`; regenerate `contracts/openapi.json`.
5. Tests (`tests/test_dataset_runs.py`, fakes only): validation matrix,
   per-item seeds incl. wrap, frozen style/item prompt reaching the fake
   provider, failure continuation, Stop, restart reconciliation without
   resubmission, idempotent same id / conflict, shared active limit with
   style runs, owner isolation/Origin, summary kind, legacy style runs and
   history rows unchanged.
6. Gate: `uv run --extra lint ruff check src tests`, `uv run python -m pytest -q`.

## Frontend (apps/web)
7. `api.ts` types (`kind`, `items`, `DatasetItem`) + `createDatasetRun`.
8. `dataset-prompts.ts` library (~120 items, ≥6 categories).
9. `dataset-run.ts` selection/validation/parameter helpers.
10. `style-run-store.ts` `startDataset`, kind-aware labels.
11. `DatasetRun.tsx` panel + entry in `App.tsx`; styles.
12. `dataset-export.ts` (zip writer, captions, sequential sanitize) and
    export entry points in `SavedResults.tsx` and history selection.
13. Gate: `npm run lint`, `npm run build` (fresh, env-free). Source review of
    lifecycle races (create ambiguity, Stop, logout, stale epochs, URL revoke).

## Specs / docs
14. Update `durable-experiment-contract.md`, `style-experiment-contract.md`,
    `api-contract.md`; add `dataset-run-contract.md` (backend + frontend
    sections); README notes on paid Start and 7-day retention.

## Review gates / rollback points
- After step 6: backend compatible and committed separately.
- After step 13: web commit. Each commit independently revertible.
- No paid generation probe; operator performs real acceptance.
