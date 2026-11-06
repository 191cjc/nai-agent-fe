# Fixed-style Dataset Runs and Training-set Export

## Scope / Trigger

Use when changing dataset (LoRA training set) runs, the built-in training
prompt library, dataset group metadata, or the browser zip export. A dataset
run is a second kind of the [Durable Experiments](./durable-experiment-contract.md)
run and inherits every lifecycle guarantee there (single create POST, known-id
reconciliation, failure continuation, explicit Stop, no paid retry, restart
reconciliation, per-owner per-lane run queue). Frontend lifecycle rules follow
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
| 10 unfinished style/dataset runs already | 409 `experiment_run_queue_full` |
| Earlier unfinished run in the same lane | Accepted; waits in queue order |
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
- The saved-experiment list always shows the merge-export bar when the page
  has training sets: per-set 「选择」 checkboxes, 「全选本页训练集」/「取消本页」, and
  「合并导出所选（N）」 (disabled until one is chosen). Selection persists across pages.
- Export captions may carry an optional user prefix (UI preset for Animagine
  XL 4.0: `masterpiece, high score, great score, absurdres`): order is trigger,
  prefix tags, then content tags, de-duplicated. Empty prefix keeps the
  previous captions exactly. Only quality tags belong there; texture/style
  features the LoRA should learn (skin gloss, eye detail) stay out of
  captions so they bind to the LoRA itself.
- Style library (2026-10-31): 109 items, all default-selected — 70 female,
  10 adult male, 14 `male child` (category `boy`), 15 no-human; mixed-gender
  and former non-default male items were removed. Every person item names hair
  colour, eye colour where visible, and coloured clothing so captions match
  the image. Child items are wholesome and fully clothed (no swimwear, bath,
  bed or suggestive tags), and the web blocks Start when any child item is
  selected together with body-shape/suggestive style tags (`CHILD_UNSAFE_STYLE`
  in `DatasetRun.tsx`). Never relax that guard.


## Image re-runs (2026-11-02)

- `POST /api/generations/{job_id}/rerun {discard_index?}` → 202
  `GenerationAccepted`. Only for the owner's terminal dataset groups
  (`422 rerun_unsupported` otherwise, `409 job_active` while queued/running,
  404 for foreign jobs or bad `discard_index`, 429 `queue_full`). One paid
  generation: the source's frozen parameters/references, `sample_count = 1`,
  new random seed, `experiment.rerun_of = <source job id>`.
- `ExperimentContext.rerun_of` is dataset-only; `create_rerun` requires a
  terminal source row of the same run/ordinal/total and an existing server
  run. Ordinary `POST /api/generations` with `rerun_of` → 409.
- Re-runs sit after their ordinal (`ORDER BY length(ordinal), ordinal,
  rowid`). Summary `group_count`/`completed_count` count run groups only;
  `image_count` includes re-runs. Run counters never change.
- When `discard_index` is given, the source image is marked discarded after
  acceptance. Export includes re-run images like any group.

## Complete captions and multi-person items (2026-11-03)

- Captions are the frozen prompts, so the library must name everything visible
  that the LoRA should *not* absorb as style: hair and eye colour (eyes may be
  omitted at wide shots), coloured upper and lower garments, and footwear or
  `barefoot` on full-body/wide/cowboy framings. Keep each item within ~30
  tags; tags the model cannot reliably render become caption noise.
- `DatasetItem.characters: [{prompt, x, y}]` (0..6, each ≤1000, non-blank, no
  `//` line under `prompt_comments`) is optional and excluded when empty, so
  stored definitions and `settings_json.experiment.item` stay byte-identical.
  `prompt` holds the shared scene (count, framing, action, background).
  Ordinal N then sends `character_prompts = item.characters` with
  `auto_character_position: false`; items without characters leave both
  untouched. Non-native models and character (reference) runs reject such
  items at create (422) through `GenerationRequest` validation.
- Web: `DatasetEntry.characters` (strings) gets evenly spaced positions in
  `datasetItems` (x = 0.1 + 0.8·(i+1)/(n+1), y = 0.5) and blocks Start on a
  non-native model. All 7 `multi` library items use characters; each person
  starts with `girl`/`boy` as NovelAI expects. Captions are scene tags then
  each person's tags, minus bare `girl`/`boy`/`other`, de-duplicated.
- Tests: `test_dataset_runs.py` multi-person send/legacy/rejection cases and
  character-run rejection.

## Prompt library import/export (2026-11-03, web only)

- `apps/web/src/prompt-io.ts`; UI in `PromptLibrary` (「批量导入」「导出已选」).
  No API change: imported entries are ordinary draft entries.
- Text format: one prompt per line; `人物：…` (or `人物:`) lines append a person
  to the previous prompt (style library only, ≤6); `# 分类：<id>` sets the
  category for following lines (unknown ids → `custom`); other `#` lines and
  blank lines are ignored; a `//` line is an error. Export writes the selected
  entries in this format with category markers, so a re-import restores
  categories — keeping `boy` items under the child-safety style guard.
- Import appends (fresh `custom-N` ids, all selected) or, after confirm,
  replaces the list; any invalid line rejects the whole import with its line
  number. Files ≤2 MiB, read locally; nothing is uploaded.

## Library composition v3 (2026-11-03)

- 156 items, all default-selected: 111 adult female (incl. `angle` 16 and
  `fantasy` 25 people), 2 adult male (operator: keep adult men to one or two),
  14 `male child` (`boy`), 6 `female child` (`girl`), 23 no-human (incl. 8
  fantasy creatures/scenery). Multi-person items: 6 everyday + 3 fantasy, all
  female, all native characters.
- `girl` follows the `boy` rules exactly: wholesome, fully clothed everyday
  scenes only, and `CHILD_UNSAFE_STYLE` blocks Start when either child
  category is selected with body-shape/suggestive style tags. Fantasy,
  demi-human and angle items are adults only; never add child fantasy items
  with revealing outfits.
- Angles: about a quarter of person items are non-eye-level (`from below`,
  `from above`, `from side`, `from behind`, `profile`, `dutch angle`, `pov`,
  `foreshortening`, one `fisheye`), captioned like any content tag.
- Demi-human features are always tagged with colour (`black horns`, `demon
  tail`, `blue scales`, `pointy ears`, `white wings`, `halo`) so the LoRA
  learns how they are drawn instead of adding them to every character.
- Fantasy share is about a fifth of the set so ordinary scenes are not
  pulled towards fantasy; keep that balance when extending.

## Library composition v4 (2026-11-05)

- 298 items (server/web cap is 300 per run; default selects all, so keep the
  library ≤300). Added 142: new category `ornate`「华丽立绘」(40) plus
  portrait/upper/full +12 each, angle +14, scene +12, light +10, multi +6,
  fantasy +12, nohuman +12. `boy`/`girl` and the 2 adult male items unchanged.
- `ornate` matches the operator's character references (adult splash-art
  goddesses): ornate gold-trimmed costumes, very long floating hair, ribbons,
  shawls and wide sleeves, crowns/tiaras/halos/mechanical halos, ornate staffs,
  orbs and weapons, hanfu with tassels and beads, glow on dark or white
  backgrounds; 34 solo, 2 multi (native characters), 4 no-human ornament props.
  Every ornament and effect (`gold trim`, `glowing`, `dark background`, `aura`)
  is captioned so the style learns to draw it instead of adding it.
- Fantasy + ornate is now about 29% (was ~21%), chosen by the operator so the
  style LoRA can render ornate character LoRAs; everyday, scene, angle and
  light categories grew by the same proportion to keep generalisation.

## Names and type badge (schema 8)

- `experiment_names(user_id, run_id, name, named_at)` holds an optional owner
  display name (1–80 chars after whitespace collapse; control/format chars
  refused; blank = unnamed). It is **not** part of the frozen definition, so a
  create retry with a different name keeps the original name and identity.
- `POST /api/dataset-runs` accepts optional `name`; `PUT
  /api/style-experiments/{id}/name` `{name: string|null}` sets/clears it (204;
  404 for unknown or foreign experiments).
- Summaries add `name` and `dataset_type` (`character` when any group carries a
  `reference`, `style` for other training sets, `null` for style experiments).
- Web: optional name field before 开始批跑; saved list shows 画风/角色 badge,
  name (or 未命名训练集) and inline rename; single-set export zips are named
  `<name>-<date>.zip`.

## Deleting a saved experiment / training set

- `DELETE /api/style-experiments/{id}` (owner only; 404 unknown/foreign) returns
  `{deleted_groups, deleted_images}`. 409 `experiment_run_active` while its run is
  running/stopping; 409 `job_active` while any group or re-run is queued/running.
- One write transaction deletes every `generation_jobs` row of the experiment
  (re-runs included; `discarded_images` cascade), its `experiment_names` row and
  its `style_experiment_runs` row. Image files and thumbnails are discarded after
  commit; a failed file removal only lingers until the 7-day sweep.
- Never touched: reference images, prompt snapshots, ordinary history. Existing
  SQLite backups still contain the deleted prompts until those backups age out.
- Web: per-item delete in the saved list (disabled for the active run) and
  「删除所选（N）」 in the selection bar; a plain confirm names every set.

## Continuing a stopped training set (2026-11-05)

- `POST /api/style-experiment-runs/{id}/continue {id: UUID}` → 202 new
  `RunState` (idempotent by the new id). Only stopped dataset runs (409
  `experiment_run_active` while running/stopping, 422 `continuation_unsupported`
  for style runs, 422 `nothing_to_continue` when every item was claimed).
- The new run holds items `next_ordinal..total` and renders each exactly as the
  original would have: base seed `item_seed(seed, next_ordinal)`, the style pool
  rotated by the offset, and img2img/precise reference order rotated by the
  offset (vibe/GPT keep all references). References must still exist with the
  pinned digest (else 422 `reference_not_found`). GPT continuations record the
  server's current model and keep the run's `parallelism`. Name gets 「（续）」.
- Already-processed failures are not included; use per-image re-run for those.
- Operator: `novelai-admin continue-run RUN_ID` does the same server-side and
  prints only ids/counts. Web: 「继续剩余 N 条」 on stopped training sets in the
  queue's finished list.

## Item canvases, editable re-runs, bangs and glosses (2026-11-05)

- `DatasetItem.width/height` (optional, both or neither, 64–2048, multiple of 64,
  excluded when absent so stored items stay byte-identical) override the run size
  for that ordinal. Every item still validates as a full `GenerationRequest`, so
  GPT runs accept only GPT sizes. Image-to-image character runs reject item sizes
  (422): the source image is sent at the run size.
- Web 「按构图自动选比例」 (default on, off for img2img): `itemShape()` in
  `dataset-run.ts` — `wide shot`/`scenery`/full-body groups → landscape, `full body`
  /`cowboy shot` → portrait, else square; NovelAI 832×1216 / 1024×1024 / 1216×832,
  GPT 1024×1536 / 1024×1024 / 1536×1024. Style library default: 114 / 127 / 57.
- `POST /api/generations/{job_id}/rerun` accepts optional `prompt` (1–1000) and
  `style_prompt` (1–3000). An edited prompt replaces `experiment.item.prompt` (the
  caption) and the sent prompt; character groups keep `<traits>, ` and swap only the
  item part. Edits are re-validated as a full request (422 `rerun_invalid` for blank,
  comment-line or over-budget input); a re-run without edits keeps the old
  `model_copy` path and is never re-validated against newer rules. The source group
  is never changed.
- Review grid counts are split: 「重跑已弃置（X）」 counts discarded images of
  succeeded groups and 「补跑失败（Y）」 failed groups, each minus re-runs already made
  from that job. Both open an editor (one optional new style, editable prompt per
  image) before the confirm; the single-image 「重跑（新种子）」 opens the same editor.
- Bangs: about 40% of style person descriptions carry one bangs tag (`parted bangs`
  ~15%, `blunt bangs`, `swept bangs`, `forehead, hair pulled back`, `sidelocks`,
  `hime cut`, `hair over one eye`); the rest leave bangs to the model.
- `apps/web/src/prompt-zh.ts`: display-only tag→Chinese glosses (every built-in
  tag) shown under each library item and in the re-run editor; never sent or
  captioned. Loaded only with the lazy dataset chunk. Keep it complete when adding
  library tags.

## Training-set cover (2026-11-06)

- `ExperimentSummary.cover_job_id` (additive, nullable): the lowest-ordinal succeeded
  group with `image_count > 0` whose image 0 is not discarded; re-runs count, ties by
  creation order. Computed in the same aggregate pass as the summary (MIN over a key of
  `printf('%06d', length(ordinal)) || ordinal || printf('%012d', row_order) || id`,
  then the trailing 36-char UUID) — never a per-set correlated query, and never
  `CAST(ordinal AS INTEGER)`: ordinals are exact decimal strings of any length.
- The cover image may have expired; the web hides the cover when the thumbnail fails.
  Web shows it only for `kind === 'dataset'`, left of the history card; click = 浏览图片.

## Durable re-run batches (2026-11-06)

- `POST /api/rerun-batches` `{id, experiment_id, items:[{job_id, prompt?, style_prompt?,
  discard_index?}] (1..3000), name?}` → 202 `RunState` with `kind: "rerun"`,
  `rerun_experiment_id`, `rerun_items`. Idempotent by id (same frozen definition);
  other content under the same id → 409 `experiment_run_conflict`.
- Validated up front, item by item (message prefixed `Item N:`): the training set
  must be the owner's dataset run (404 / 422 `rerun_unsupported`); every source must
  be a finished group of that set (422 `rerun_source_missing`, 409 `job_active`);
  edits and discard index use the single re-run rules (`reruns.rerun_parameters`,
  shared with `POST /api/generations/{id}/rerun`; 422 `rerun_invalid` /
  `rerun_image_missing`). GPT sets need the GPT provider (503).
- Stored as a `style_experiment_runs` row (no schema change): definition
  `{kind:"rerun", plan_version:2, parameters:<set's run parameters, sample_count 1>,
  experiment_id, sources:[...]}`, lane = the set's lane, total = item count. It joins
  the owner's lane queue in creation order and shares stop / continue / outage pause
  / restart recovery / GPT parallelism / MAX_ACTIVE_RUNS with other runs.
- Each ordinal: re-read the source job and build its re-run parameters (new random
  seed, one sample). `RunStore.claim_rerun` persists the re-run job (via
  `create_in_transaction(rerun=True)`), the in-flight row, the cursor and the optional
  discard mark of the replaced image in one transaction before any paid call.
- A source that is gone, moved or no longer valid is counted failed without a job
  (`skip_rerun`, error `rerun_source_missing` or the refusal code); no retries.
- Continue (`/style-experiment-runs/{id}/continue`) on a stopped batch queues a new
  batch of the never-claimed sources, name + 「（续）」.
- Batches own no generation rows, so they never appear in the saved-experiment list.
- Release note: the browser-loop single re-runs are gone from the grid. Before the
  first deploy of this, still queued single re-runs were failed as
  `rerun_cancelled` (never paid) and running ones fall to `outcome_unknown`.

## No-human fantasy items live in `nohuman` (2026-11-06)

- The 8 `no humans` items of `fantasy` (dragons, slime, floating island, town,
  dungeon, magic circle, treehouse village) moved to the end of `nohuman`, so a
  category run of 「无人物」 includes them and 「异世界奇幻」 is people only. Total stays
  298. Item ids are positional: later `fantasy-N` ids and the moved items' ids
  changed; frozen runs keep their old ids (only the grid's category filter reads them).
