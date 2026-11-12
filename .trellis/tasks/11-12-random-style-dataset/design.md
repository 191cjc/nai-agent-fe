# Design: random style dataset recipes

## Overview

```
RecipeEditor (web) ──PUT──▶ dataset_recipes (SQLite, schema 14)
       │
       └─POST /api/dataset-recipes/sample {recipe, n, seed}──▶ recipe_engine (pure, deterministic)
             ◀── items[{id, prompt, width?, height?, draws, style_edits}] + stats
draft entries (existing list, editable) ──POST /api/dataset-runs──▶
   item frozen (draws + style_edits) in definition_json and settings_json.experiment.item
   dataset_parameters(): style = pool[ordinal] − style_edits.remove + style_edits.add
ReviewGrid ── job.parameters.experiment.item.draws ──▶ client-side draw/rule filter
export caption ── item.prompt only (unchanged) ──▶ style_add tags never captioned
```

The engine runs on the backend: recipes live there, pytest can property-test
it over thousands of seeds (the web app has no test runner), and one
implementation keeps preview and generation consistent. It is pure, with no
I/O and no provider calls, so previews are free.

## Core concepts

| Concept | Meaning |
|---|---|
| **Region** | Something that may or may not be visible. Recipe-defined, each with an optional `parent`; hiding a region hides all its descendants. Defaults: `person` ⊃ {`face` ⊃ `eyes`, `upper`, `lower` ⊃ `feet`, `hands`}. All visible at start. |
| **State** | String key → string value set by options (`shot=upper`, `pose=sitting`, `gender=female`, `age=adult`, `time=night`). |
| **Resource** | Counted capacity (`hands: 2`, `top: 1`, `bottom: 1`), recipe-defined. |
| **Condition** | Boolean tree evaluated against the item being built (below). |
| **Effects** | One shared effect set used by options (incl. `none`) and rules: structural `hide`, `set`, `consume`, `remove_partitions`, `remove_options`; tag-level `content_add`, `remove_tags`, `style_add`, `style_remove`. |
| **Slot** | Recipe-level weighted value list (e.g. `color`). Option tags use `{color}` placeholders filled per draw, producing one tag (`red kimono`). |
| **Only-allow** | Effect `allow_options: {partition: [option ids]}` (and `allow_values: {slot-use: [values]}`): later draws of that partition are restricted to the list. |
| **None option** | A per-partition option with no tags: drawing it deliberately skips the partition, yet its effects apply. |
| **Rule** | Post-draw: `when` condition ⇒ effects (removal and tag edits; `hide`/`set`/`consume` are not allowed in rules). |

### Identity: ids, never names

- Every partition, option, slot, slot value, region, resource, state key and rule
  has an **immutable id**, generated once when it is created. Labels (Chinese
  names) are free text and freely renamable. All references (conditions,
  effects, orders, whitelists, draw records, review filters, stats) use ids.
  Renaming a partition therefore changes nothing but its label.
- Id generation:
  - **Recipe id**: UUID v4 from `crypto.randomUUID()` in the browser, sent with
    an idempotent `PUT` (same pattern as dataset run ids).
  - **Objects inside a recipe**: the editor generates `<type prefix>-<8 base36>`,
    for example `p-k3x9q2mf` for partitions. Prefixes are `p` partition, `o`
    option, `s` slot, `v` slot value, `g` region, `r` rule, `c` resource and
    `k` state key.
    - The random part is 40 bits from `crypto.getRandomValues`, written as 8
      base36 digits.
    - Uniqueness is checked within the id's scope: option ids are unique per
      partition, slot value ids per slot, all others per recipe. A collision
      is regenerated.
  - Ids are **not derived from names or tags**. A tag-derived slug would become
    misleading when the tag later changes (`pleated-skirt` holding
    `plaid skirt`).
  - The built-in basic template uses fixed hand-written ids (`framing`, `top`,
    `school-uniform`). They are stable because the template is authored in
    code. A recipe created from the template keeps them, so draws from several
    recipes based on the same template group together in review.
  - **Reserved ids**: `none` for the none option. Synthetic draw markers start
    with `-` (`-skip`, `-removed`, `-rule`, `-style`, `-meta`). The id pattern
    `^[a-z0-9][a-z0-9-]*$` forbids a leading `-`, so a marker can never
    collide with a real id.
  - **Copy**: copied objects get new ids, and references *inside* the copied
    set are remapped to the copies.
  - **Import**: a whole recipe keeps its ids. Merging partitions from another
    recipe regenerates only colliding ids and remaps their references.
  - **Duplicate recipe**: new recipe UUID; inner ids are unchanged, because
    they are scoped to the recipe.
  - The backend never generates object ids. It only validates the format,
    uniqueness and references.
  - Sampling never depends on id values. It follows array order, so changing
    an id never changes the drawn results.
- Ids are never edited in the normal UI. An advanced
  「修改 ID」 action rewrites every reference atomically and warns that old run
  records keep the old id.
- An option is referenced by the pair `{partition id, option id}`. Option ids
  only need to be unique within their partition. The JSON shorthand
  `"bottom.pleated-skirt"` is used below for readability; the stored form is
  the same dotted pair.
- Deleting a partition/option/slot value that is still referenced is blocked.
  The editor lists the referencing places ("被 3 处引用") with a 「同时删除这些
  引用」 option.
- Draw records store ids **and** the label snapshot at draw time. The review
  filter groups by id and shows the latest label from the current recipe when
  it still exists, otherwise the stored one.

### Condition language (JSON, built by dropdowns in the UI)

```jsonc
{"all": [c, ...]} | {"any": [c, ...]} | {"not": c}
{"chosen": "hands.two-hand-sword"}          // an option was drawn
{"partition_drawn": "shoes"}                 // the partition produced ≥1 option
{"state": "pose", "in": ["sitting", "standing"]}
{"visible": "eyes"}
{"tag": "smile"}                             // normalized tag present in the current content
```

Evaluation is pure. During drawing it sees only what has been drawn so far.
In the rule phase it sees the complete item. Depth ≤ 8, ≤ 64 nodes per condition.

### Recipe JSON (`DatasetRecipe`, version 1)

```jsonc
{
  "version": 1,
  "regions": [{"id": "person"}, {"id": "face", "parent": "person"}, {"id": "eyes", "parent": "face"},
              {"id": "upper", "parent": "person"}, {"id": "lower", "parent": "person"},
              {"id": "feet", "parent": "lower"}, {"id": "hands", "parent": "person"}],
  "resources": {"hands": 2, "top": 1, "bottom": 1},
  "slots": [
    {"id": "color", "label": "颜色",
     "values": [{"id": "white", "tag": "white", "zh": "白色", "weight": 10},
                {"id": "red", "tag": "red", "zh": "红色", "weight": 8},
                {"id": "green", "tag": "green", "zh": "绿色", "weight": 4}]}
  ],
  "glossary": {"china dress": "旗袍", "pleated skirt": "百褶裙"},   // recipe translations, see "Translations"
  "style_tags": [                                    // region-bound tags of the style prompt
    {"tag": "detailed eyes", "needs": "eyes"},
    {"tag": "beautiful hair", "needs": "person"}
  ],
  "draw_order":   ["scene", "framing", "view", "subject", "hair-length", ...],
  "prompt_order": ["subject", "framing", "view", "hair-length", ..., "scene", "time"],
  "partitions": [
    {
      "id": "scene", "label": "场景",
      "mode": "one",                       // "one" | "fill" (repeat; drawing none stops)
      "max_draws": 1,
      "quota": false,                      // proportional allocation over N
      "when": null,                        // partition condition; false ⇒ skipped ("condition")
      "needs": [],                         // regions; any invisible ⇒ skipped ("invisible")
      "options": [
        {"id": "empty-street", "label": "无人街道", "tags": "no humans, street, scenery",
         "weight": 10,
         "weight_mods": [{"when": {"state": "time", "in": ["night"]}, "factor": 0.5}],
         "when": null, "needs": [],
         "effects": {"hide": ["person"], "set": {}, "consume": {},
                     "remove_partitions": [], "remove_options": [],   // see "Removal"
                     "content_add": [], "remove_tags": [], "style_add": [], "style_remove": []},
         "child": false, "size": "landscape"},
        {"id": "qipao", "label": "旗袍", "tags": "{color} china dress", "zh": "{color}旗袍", "weight": 6,
         "slots": {"color": {"exclude": ["green"], "weight_mods": {"red": 2},
                             "set_state": "top_color"}},
         "effects": {"consume": {"top": 1, "bottom": 1}}},
        {"id": "none", "none": true, "label": "不写场景", "tags": "", "weight": 5,
         "effects": {"style_add": ["simple background"]}}
      ]
    }
  ],
  "rules": [
    {"id": "gentle-smile", "label": "笑容柔和化",
     "when": {"tag": "smile"},
     "effects": {"style_add": ["gentle smile"]}}
  ]
}
```

`draw_order` and `prompt_order` are permutations of the partition ids, both
reorderable in the editor. When `prompt_order` is omitted it defaults to
`draw_order`. Omitted effect keys default to empty.

### Slots (attribute combinations inside one tag)

- A slot is a shared weighted value list. Values have `id`, `tag` (English),
  `zh` and `weight`. Options reference slots through `{slot}` placeholders in
  `tags`, and optionally in `zh`. `{color} {pattern} kimono` uses two slots;
  each placeholder name may appear once per option.
- Per option and slot: `exclude` / `only` (value ids), `weight_mods` (value id
  → factor), `set_state` (state key that receives the value id), and `when`
  conditions on values (e.g. `not same as state top_color` written as
  `exclude_state: "top_color"`).
- The engine draws the option first and then each placeholder, in text order,
  from the filtered and reweighted values. If no value survives, the option
  is ineligible. This is checked *before* the option is drawn, so the option
  is filtered out instead of failing afterwards.
- The filled text is one tag: whitespace is normalized, there is no comma
  inside, and removal and `{"tag": …}` conditions see the filled tag.
- Draw records gain `values: {color: "red"}`, and labels use the filled `zh`
  (`红色旗袍`). The review filter offers slot values as their own chip group
  per partition (上装 · 颜色).
- Stats report per-slot-value shares per partition.
- Validation: placeholders reference existing slots, value ids are unique, no
  placeholder in `none`, and ≤ 20 slots × 100 values.

### Only-allow (whitelist) effect

- `allow_options: {"bottom": ["pleated-skirt"]}`: from then on that partition
  may only draw the listed options (its `none` option is still allowed only
  if it is listed). `allow_values: {"bottom.pleated-skirt.color": ["navy",
  "black"]}` restricts slot values the same way.
- It is the counterpart of `remove_options`. Several whitelists on the same
  target intersect. An empty intersection makes the partition skip with reason
  `conflict`.
- An already drawn option outside a new whitelist is withdrawn, using the
  same withdrawal semantics as removal. The editor's ordering warning suggests
  drawing the whitelisting partition first (school uniform → bottom).
- Rules may also use `allow_options` as a post-draw withdrawal.

### None option (replaces partition probability)

- Any partition may contain **one** option with `none: true`. It must have empty
  `tags`. Like any option it has a weight, conditions, `weight_mods` and
  effects. Its share is how often the partition is deliberately left out. A
  "30 % 饰品" partition is simply none weight 70 against 30 for the real options.
  There is no separate `probability` field, so there is only one way to express it.
- Drawing `none`:
  - records `{partition, option: "none", label: "<分区>：无"}`, filterable in review;
  - counts as *not drawn* for `partition_drawn`;
  - is still `chosen` for `{"chosen": "shoes.none"}`, so a rule can react to
    it (e.g. `shoes.none` ∧ visible `feet` ⇒ `content_add barefoot`).
- In `fill` mode, `none` is eligible at every draw. Drawn first, it leaves the
  partition empty; drawn later, it stops further draws (its weight against the
  real options sets how many are drawn). Its effects apply only when it is the
  first draw. This replaces `stop_probability`.
- `none` takes part in quota allocation like other options.
- `none` is different from a skip. A skip (invisible, condition, removed,
  conflict) is decided by the recipe structure and applies no effects; `none`
  is a weighted choice whose effects do apply.

### Effect timing

- Structural effects (`hide`, `set`, `consume`, `remove_partitions`,
  `remove_options`) take effect immediately when an option is drawn, so later
  draws see them.
- Tag-level effects (`content_add`, `remove_tags`, `style_add`, `style_remove`)
  from options are collected and applied at assembly. They apply in draw
  order, then the rules' tag effects in rule order. Later effects override
  earlier ones for the same tag. A tag removed by a later effect is not
  re-added by an earlier one.

### Removal (three granularities, two timings)

| Target | Option effect (during draw) | Rule effect (after draw) |
|---|---|---|
| Partition `remove_partitions: ["eye-color"]` | not yet drawn ⇒ skipped (`removed:<option>`); already drawn ⇒ withdrawn | withdrawn / never shown |
| Option `remove_options: ["hands.wave"]` | not yet drawn ⇒ ineligible; already drawn ⇒ withdrawn | withdrawn |
| Tag `remove_tags: ["blue eyes"]` | removed at assembly | removed at assembly |

- Examples:
  - no-human scene: `remove_partitions` lists every person partition, or
    the option hides region `person`; both work.
  - `closed eyes`: `remove_partitions: ["eye-color"]`. It works whether
    eye colour is drawn before or after expression.
- **Withdrawal** of an already drawn partition/option removes its tags and
  records `{partition, option: "-removed", label: "…被<来源>移除"}`.
  - Its `consume` is refunded.
  - Its `hide` and `set` effects are reverted **only if no later draw
    depended on them**. The engine keeps an effect log per draw and recomputes
    visibility/state from the surviving draws. If a later surviving draw had
    used that state or visibility (its eligibility was evaluated while it
    held), the withdrawal still happens; the dependent draw is kept, and the
    item stats flag `stale_dependency` so the editor can suggest a better order.
  - Nothing is redrawn after a withdrawal, so a removed partition stays empty.
- `hide`/`needs` (regions) remain the general mechanism for "a whole class of
  partitions disappears" (`person`, `lower`, `feet`). `remove_*` names concrete
  targets. Both coexist; regions also drive region-bound style tags. A
  partition removed by name also counts as "not drawn" for
  `partition_drawn` conditions.
- Region implication comes from the recipe's region tree (`person` hidden ⇒
  its descendants hidden). No-human has no special-case code. Regions can be
  added (e.g. `tail`, `wings` under `person`) without code changes. Validation
  requires unique ids, existing parents and no cycles, with ≤ 32 regions.
- Removal never applies to the caller's own partition. Validation rejects
  self-references and unknown targets.

### Static validation (all errors name a JSON path)

- ids `^[a-z0-9][a-z0-9-]*$`; ≤40 partitions, ≤200 options each, ≤4000 options,
  ≤100 rules, tags ≤300 chars, no `//` line, weights > 0; at most one `none`
  option per partition, with empty tags; rules may not use `hide`/`set`/`consume`.
- References resolve: `chosen`/`partition_drawn` targets exist, regions are in
  the vocabulary, resources are declared, orders are exact permutations.
- **Draw-time conditions may only reference partitions earlier in
  `draw_order`** and state keys set by earlier partitions. A forward reference
  would silently read "not yet chosen", so it is an error, not a warning. Rules
  have no such restriction.
- Ordering warning (non-blocking, shown in the editor): an option hides
  region R while a partition or option that needs R is drawn **earlier**. The
  earlier draw cannot be undone by `hide`, so the editor suggests moving it
  later or adding `remove_partitions`.
- `quota` is only allowed on partitions with no `when`/`needs`, mode `one`, and
  options with no `when`/`weight_mods`. Otherwise the
  allocation would be broken by filtering.
- Child safety: an option with `child: true` must `set age=child`. Any option or
  rule tag matching the unsafe keyword list (swimwear, underwear, nude, bed,
  bath, plus the `CHILD_UNSAFE_STYLE` body/suggestive words) must be guarded
  with a `when` that implies `not state age=child`. This uses a conservative
  syntactic check: the condition must be an `all` containing that `not` clause,
  or exactly that clause. `style_add` rules whose condition does not imply
  adult age may not add unsafe words.

## Engine algorithm (`recipe_engine.py`)

```
rng = random.Random(seed)
quota[p] = largest-remainder allocation of n over p.options weights → list, rng.shuffle
for i in 0..n-1:
  st = {visible: ALL, state: {}, cap: copy(resources), chosen: {p: []}, content_tags: [], skips: {}}
  for p in draw_order:
    if p.when and not eval(p.when, st):                   skip(p, "condition"); continue
    if any region in p.needs not visible:                 skip(p, "invisible"); continue
    k = 0
    loop:
      cands = [(o, w) for o in p.options if eligible(o, st) for w in [eff_weight(o, st)] if w > 0]
      if not cands: if k == 0: skip(p, "conflict"); break
      o = quota[p][i] if p.quota else weighted_choice(rng, cands)
      apply(o, st)   # withdraw o.remove_* targets already drawn; block the rest;
                     # visible -= o.hide (person ⇒ all); state |= o.set; cap -= o.consume;
                     # chosen[p] += o; content_tags += normalize(o.tags)
      k += 1
      if o.none or p.mode == "one" or k == p.max_draws: break
  # Rule phase: single ordered pass in recipe order. Conditions see the full item
  # plus earlier rules' content edits; style edits do not feed back into conditions.
  for r in rules: if eval(r.when, st): withdraw partitions/options; content add / remove_tags; style_add/remove accumulate; hit(r)
  # Region-bound style tags: for each style_tags entry whose region is invisible → style_remove
  prompt = join(tags of chosen options in prompt_order) + content_add − remove_tags,
           normalized, de-duplicated; ≤1000 chars else item reported as overflow (never truncated)
eligible(o, st) = o.id not in chosen[p] ∧ not blocked(p or o) ∧ needs ⊆ visible ∧ eval(o.when) ∧ cap ≥ o.consume
eff_weight(o, st) = o.weight × Π factor of weight_mods whose when holds
```

- Quota partitions use the pre-allocated option. Validation guarantees it is
  always eligible.
- **Style edits** are stored per item as `{add: [...], remove: [...]}`.
  Removal of a tag absent from the chosen style is a no-op. Additions skip
  tags already present.
- **Stats** (returned with the sample):
  - per option (incl. `none`): target share (weight share; shown as a
    "conditional target" for `when`/`needs` partitions), actual count, deviation;
  - per partition: skips by reason;
  - per rule: hit count;
  - per style tag: removal count.
  Deviations over 5 percentage points are highlighted.
- Items with no `person` visible get `size` from their scene option. Otherwise
  the last chosen `size` hint wins, falling back to `itemShape()`.
- Item ids: `r{seed}-{i:04d}`.

## Stored per item (`DatasetItem` additions, all optional and excluded when empty)

```jsonc
"draws": [{"partition": "scene", "option": "empty-street", "label": "场景：无人街道"},
          {"partition": "subject", "option": "-skip", "label": "主体：未出现(invisible)"},
          {"partition": "-rule", "option": "gentle-smile", "label": "规则：笑容柔和化"},
          {"partition": "-style", "option": "detailed-eyes-removed", "label": "画风：去掉 detailed eyes"}],
"style_edits": {"add": ["gentle smile"], "remove": ["detailed eyes"]},
"recipe": {"id": "<uuid>", "name": "…"}
```

Limits: draws ≤128 entries; style edits ≤32 tags each, ≤100 chars per tag, no
`//` or emphasis syntax. Pydantic's default `extra="ignore"` means an old API
build still loads rows with these keys. A test pins this.

## Backend run changes

- `dataset_parameters()` resolves the item style. The pool style is chosen
  exactly as today, then edited tag-wise:
  - parse with the existing `prompt_weights` tokenizer;
  - remove a tag when its normalized text, with weight syntax stripped,
    matches;
  - append additions at the end. Plain tags only.
  `prompt_comments` hidden lines are preserved.
- Create-time validation resolves the style for every ordinal, rejects a
  blank or comment-only result (422), and runs the existing full
  `GenerationRequest` validation, which includes the 3000-character limit.
- Re-runs copy the frozen item, so they get identical style edits.
  `provider_request_json` captures the resolved style as today.
- Character runs reject items with `style_edits` (422). They are style-run only.

## Translations (zh glosses)

- Every English tag in a recipe (option tags, slot value tags, rule tags,
  style tags) has a Chinese gloss, resolved in this order:
  1. per-option `zh` (template text with placeholders, for combinations like
     `{color}旗袍`);
  2. the recipe `glossary` (tag → zh, user-entered or chosen from search);
  3. the built-in `TAG_ZH` dictionary in `apps/web/src/prompt-zh.ts`
     (~2200 entries, display only);
  4. otherwise the gloss is **missing**.
- Glosses are display-only: they are never sent to the provider and never
  enter captions. They are stored with the recipe (so JSON export carries
  them) and in each draw label (so the review filter reads in Chinese after
  the recipe changes).
- The editor shows the gloss under every tag chip. Missing glosses are
  highlighted, with two actions:
  - 「手动输入」 writes the gloss to the recipe glossary.
  - 「查找」 calls the existing `POST /api/tags/search` with the English tag and
    shows candidates (`tag`, `cn_name`, category, count, NSFW flag). Picking
    one stores its `cn_name`; it can also replace the tag with the canonical
    Danbooru spelling when the user chooses so.
  The search box also accepts Chinese, so "新增选项" can start from `旗袍` →
  `china dress` (the provider already accepts Chinese queries, e.g. 蓝色长发).
- 「查找全部未翻译」 runs one search at a time (the API allows one in-flight
  search per user), is abortable, stops on 429 and shows the `Retry-After`,
  and never overwrites existing glosses. Results are proposals the user
  confirms in a list before they are written.
- An option's Chinese `label` defaults to its resolved gloss and stays editable.
- A recipe never fails validation because a gloss is missing; it only shows a count.
- The engine treats `zh` as opaque text. The backend validates its length only
  (≤ 100 chars per gloss, ≤ 5000 glossary entries).

## Basic template (default recipe)

- `recipe_templates.py` defines `BASIC_TEMPLATE`, a valid recipe:
  - the default region tree and resources;
  - the recommended partitions, in the recommended draw and prompt orders;
  - each partition gets 2–4 example options plus a `none` option where
    leaving it out makes sense;
  - colour slots used by the clothing partitions (e.g. `{color} china dress`
    excluding green), and the school uniform restricting the bottom to a
    `{color} pleated skirt`;
  - glosses for every template tag;
  - the example rules: `smile` ⇒ style `gentle smile`; closed eyes removes
    eye colour; `shoes.none` with visible feet ⇒ `barefoot`; night ⇒ style
    removes `sunlight`; `detailed eyes` bound to `eyes`.
  It contains no content from the deleted 322-item library.
- `GET /api/dataset-recipes/templates/basic` returns it. "新建配方" offers
  「空白」 or 「基础模板」. When the owner has no recipes, the editor opens a
  draft from the template (it is not saved until the user saves it).
- A test pins that the template validates and samples n=400 without overflow
  and with zero `stale_dependency`.

## Web changes

- Delete `dataset-prompts.ts`. `defaultDatasetEntries()` now returns `[]`.
  Remove the style-category UI and dead imports. Character libraries stay.
- `RecipeEditor.tsx`:
  - recipe picker (list, new, duplicate, delete, JSON import/export);
  - two ordering lists (draw order and prompt order), each with drag and up/down,
    plus 「按推荐排序」. The editor shows ordering warnings inline;
  - region tree editor (add/rename/delete regions with parent);
  - partition cards with option rows (tags, label, weight, effects, condition
    builder, weight modifiers);
  - a rules table, and a style-tag region table with the existing style
    pre-scanned for suggestions;
  - sample controls (N, seed dice, 「预览 20 条」, 「生成 N 条到列表」
    append/replace), with a stats panel beside the preview. The preview shows
    the item content and the resolved style per item, highlighting adds and
    removes.
- `DatasetEntry` gains `draws`, `styleEdits` and `recipe`, which pass through
  `datasetItems()`.
  - The item list shows a compact draw summary and style-edit badges.
  - Editing an entry's prompt adds `{-meta, edited}`. It keeps `style_edits`
    as they are, but shows a warning, because the rule may no longer apply.
- Child Start guard: for every selected entry with a `child` draw, check
  `CHILD_UNSAFE_STYLE` against the item's **resolved** style (pool style + edits).
- `ReviewGrid` gets a filter panel built from the loaded groups' draws:
  partitions (incl. `-rule`, `-style`, `-meta`) as groups, options as chips
  with counts; AND across groups, OR within. It composes with the existing
  filters. The detail tile shows the resolved style edits. The 11-10 modal
  state preservation stays intact.

## Schema 14

```sql
CREATE TABLE dataset_recipes (
    user_id TEXT NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    recipe_json TEXT NOT NULL CHECK(length(recipe_json) <= 1048576),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, id)
);
```

## API

| Route | Body → Response |
|---|---|
| `GET /api/dataset-recipes` | → `[{id, name, updated_at}]` |
| `GET /api/dataset-recipes/{id}` | → `{id, name, recipe, updated_at}`; 404 foreign/missing |
| `PUT /api/dataset-recipes/{id}` | `{name, recipe, expected_updated_at?}` → upsert; 409 `recipe_conflict` when stale; 409 `recipe_limit` above 100 per owner |
| `DELETE /api/dataset-recipes/{id}` | 204; runs keep their frozen draws |
| `POST /api/dataset-recipes/sample` | `{recipe, n (1..400), seed (uint32), styles?}` → `{items, stats}`. `styles` lets the preview show resolved styles and pre-check blank results. 422 errors carry the JSON path |

All routes are owner-scoped and mutations are Origin-checked. The OpenAPI
snapshot and the `api.ts` checkers are updated together.

## Bulk editing

The option list of every partition (and slot value lists) supports
multi-select: checkbox, shift-click range, 「全选 / 按筛选全选」 and a text filter
over tags, labels and glosses. Selection can also span partitions from a global
「全部选项」 view.

Bulk actions on the selection:

- **Add / remove effect entries**: any effect type, i.e. `remove_tags`,
  `content_add`, `style_add`, `style_remove`, `remove_partitions`,
  `remove_options`, `allow_options`, `allow_values`, `hide`, `set`, `consume`.
  - The dialog edits one effect and shows a diff preview: "12 个选项将新增
    remove_tags: pleated skirt；3 个已存在，跳过".
  - Removing applies only to that exact entry.
- **Conditions**: add an AND clause to every selected option's `when`
  (e.g. `not chosen top.school-uniform`), or remove an identical clause.
- **Weights**: set, multiply, or normalize so the selection sums to a target share.
- **Slots**: attach a slot to every selected option, or set its exclude/only lists.
- **Move / copy** to another partition (ids regenerated on copy; references
  updated on move), **delete** (with the reference check above), and
  **enable / disable**. A disabled option is kept but never drawn, which is
  handy when experimenting.

Reverse direction: from any option or partition, 「谁引用了它」 lists all
conditions and effects that point at it. Each entry links to its source, and
the entries can be bulk-removed.

Every bulk change is one undoable step. The editor keeps an in-memory undo/redo
stack of recipe snapshots (≤ 50) until save. Saving runs full validation
first and shows path-addressed errors.

## Extensibility

The design is meant to absorb future requirements without rewrites:

- **One effect registry, one condition registry.** Each effect/condition kind is
  defined once:
  - backend: Pydantic schema, validator, engine handler (structural or
    tag-level phase), stats hook;
  - frontend: editor widget, summary text, bulk-editor support.
  A new rule kind means adding one entry on each side plus tests; the engine
  loop, storage, run creation and review filters stay unchanged.
- **Versioned recipes.** `version` plus ordered migration functions
  (`migrate_v1_to_v2`, …) run when a recipe is loaded or imported, so stored
  and exported recipes keep working after schema changes. Tests keep a frozen
  v1 fixture.
- **Generated items are frozen**: runs store only prompt, draws and style
  edits, never a live reference to the recipe. Engine changes can't
  retroactively alter existing training sets or their filters.
- **Pure engine with property tests**: invariants (visibility, resources,
  whitelists, slot exclusions, determinism) are tested over many seeds, so
  refactors are checked mechanically.
- Known harder future extensions:
  - **multi-person**: needs per-person state and resource scopes; the
    item/caption pipeline already supports characters;
  - **backtracking or redraw after withdrawal**: changes stats semantics.
  Both fit the registry model but need design work of their own.

## Compatibility / rollback

- Additive table and optional item fields: old runs, exports, re-runs and
  captions are unchanged.
- Rollback to an older API: rows still load (extra keys ignored), but new
  items would be generated **without** style edits or draws if re-run. Only
  roll back when no recipe-based run is unfinished; this is documented in the
  deployment notes.
- Deploy order: migrate → API → web.

## Risks

- Hidden style rules occupy the tag they modify. For example, `smile` in this
  LoRA will lean towards a gentle smile. The UI's rule help text explains this
  so the operator can keep explicit variants (`grin`, `laughing`) as separate
  options that don't trigger the rule.
- Complex recipes can over-constrain. Skip reasons, stats and the forward
  reference validation make this visible; there is no silent fallback.
- Determinism holds per deployment (Python's `random`). Generated items are
  frozen, so cross-version reproducibility isn't required.
