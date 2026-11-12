# Implementation plan

Constraints: work only on source code, synthetic fixtures and fakes. Never read
the SQLite DB, `generation-images/`, exported sets or captions. No paid
provider calls.

## Phase A — backend sampler (pure)
1. `apps/api/src/novelai_api/recipe_engine.py`:
   - Pydantic `DatasetRecipe`, `Partition`, `Option`, `Rule`, `Condition`,
     with static validation: ids, limits, vocabulary, permutation orders,
     forward-reference ban for draw-time conditions, quota restrictions,
     child-safety guards;
   - effect and condition registries (one entry per kind: schema, validation,
     engine handler, stats hook); recipe `version` + migration chain;
   - condition evaluator;
   - `sample(recipe, n, seed, styles?) -> (items, stats)`, covering draw
     order vs prompt order, weight mods, fill mode, rule phase, region-bound
     style tags and style edits;
   - `resolve_style(style, edits)`, built on the `prompt_weights` tokenizer.
2. `tests/test_recipe_sampler.py` with a synthetic recipe fixture
   (`tests/fixtures/recipe_basic.json`, invented content). It covers:
   determinism; quota exactness ±1; weighted convergence (n=4000, tolerance);
   visibility (upper/portrait never yields lower/feet partitions, back view
   never yields expression/eyes, no-human skips every person partition and
   removes `detailed eyes`); resources (two-hand vs one-hand, outfit vs
   top/bottom); conditions (all/any/not/state/tag); conditional weights
   (statistical); rules (`smile` ⇒ style_add `gentle smile`); slots (fill, exclude/only/reweight,
   set_state, ineligible when empty); allow_options/allow_values (intersection,
   withdrawal); none options (effects,
   fill stop, quota); custom region tree; basic template validity; removal of
   partitions/options/tags during draw and in rules (before/after drawn,
   resource refund, state revert, stale_dependency flag); rules
   referencing later partitions; skip reasons; the 1000-char overflow report;
   resolve_style (weighted tags, comments, blank result); validation error
   paths including forward references and dangling/self references;
   rename invariance; v1 fixture migration; child-safety rejections.
   Review gate: the sampler tests pass before any API work.

## Phase B — storage and API
3. `migrations/0014_dataset_recipes.sql`, register it in `db.py` and probe it
   for readiness. Update the database-guidelines schema list.
4. Recipe repository plus routes (list/get/put with optimistic `updated_at`,
   delete, sample, `templates/basic` from `recipe_templates.py`). Apply the owner scoping, Origin check and limits.
5. Add `DatasetItem.draws`, `style_edits` and `recipe` (optional, excluded
   when empty). `dataset_parameters()` applies the style edits. Create-time
   validation resolves every ordinal and rejects a blank style; character runs
   reject `style_edits`.
6. Tests: `tests/test_dataset_recipes.py` (CRUD, owner isolation, Origin, 409s,
   sample endpoint). In `test_dataset_runs.py`: draws frozen into
   settings_json and returned in views; the fake provider receives the resolved
   style (gentle smile added, detailed eyes removed) while the item prompt has
   neither; legacy byte-identity; re-runs copy draws and edits; old-row and
   unknown-key tolerance.
7. Regenerate `contracts/openapi.json` and confirm `test_api_contract.py` passes.

## Phase C — web
8. `api.ts`: recipe types, checkers and client methods; `draws` on dataset item types.
9. Delete `dataset-prompts.ts`. `defaultDatasetEntries()` now returns `[]`.
   Remove the style-category UI and dead imports. Rework the child guard to use
   draws' `child` flag.
10. `RecipeEditor.tsx`: picker, partition and option editing, slot editor,
    translation chips (TAG_ZH → glossary → manual / tag search, batch lookup),
    generated ids with renamable labels, multi-select bulk editor with diff
    preview, reference finder, guarded delete, undo/redo stack, dropdown rule
    editor, JSON import/export, sample preview with a stats table, and
    append/replace into the draft list. `DatasetEntry.draws` passes through
    `datasetItems()`; hand edits add the `-meta/edited` draw and a style-edit
    warning. The child guard checks each entry's resolved style.
11. `ReviewGrid.tsx`: a draw filter panel with counts, composed with the
    existing filters (including the `-rule`, `-style` and `-meta` groups) and
   keeps the 11-10 modal state preservation intact. The detail view shows
   style edits.
   - Web caption check by source review: `dataset-export.ts` keeps deriving
     captions from `item.prompt` only, so `style_add` tags are never captioned.
12. `styles.css` for the new panels. Update the Chinese hint text in `DatasetRun.tsx`.

## Phase D — specs and verification
13. Update `.trellis/spec/backend/dataset-run-contract.md`: add a "Random
    recipes" section and mark the library sections historical. Add a new
    `dataset-recipe-contract.md` and link it in both spec indexes.
14. Backend: run the commands from `quality-guidelines.md`, with keys unset:
    ```
    cd apps/api && uv sync --frozen --extra test --extra lint
    env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra test --extra lint python -m pytest -q
    uv run --frozen --extra lint ruff check src tests
    uv lock --check --offline
    ```
    Web: `cd apps/web && npm run lint && npm run build`.
15. Operator acceptance (manual): build a recipe, preview, generate a small
    run, filter its thumbnails by draws. The operator inspects the images
    personally.

## Rollback points
- After A: the sampler is unused code.
- After B: additive table and fields. The old web ignores them.
- Deploy: migrate first, then API, then web. Web rollback alone is safe. API
  rollback drops only draws on new runs (see design).
