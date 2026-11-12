# Random style dataset recipes

## Goal

Replace the fixed built-in style-LoRA prompt library with a random generator.
The operator edits a **recipe**: weighted options grouped into partitions
(framing, appearance, clothing, pose, expression, scene, ...). The generator
draws N single-person prompts that respect the weights and never contain
contradictory or invisible content. Recipes are saved on the server, and every
generated item records what was drawn, so the training-set thumbnail list can
later be filtered by those draws for review.

## Decisions (operator, 2026-11-12)

1. Single-person items only (plus optional no-human items). Multi-person is out of scope.
2. Recipes are stored in the backend database. Each generated item's draws are
   stored with the run, so a thumbnail list can be filtered by them.
3. The existing built-in style library (`dataset-prompts.ts`, 322 items) is
   deleted. There is no built-in default recipe. Character-mode libraries are
   not affected.
4. Partitions are user-editable; the list in the request was an example.

## Requirements

### Recipe
- The style box stays first and is unchanged (style or style pool, never captioned).
- Partitions are fully user-defined: create, rename, delete, and reorder both
  the draw order and the prompt order. Each partition has an id, a Chinese
  label, a draw mode (one option, or repeated draws until capacity runs out or
  `none` is drawn) and a list of options.
- Every partition may have a **`none` option** (无) with its own weight. Drawing
  it deliberately leaves the partition out, but its effects (add/remove
  partitions, options, tags and style tags; hide regions; set state) still
  apply. It replaces a separate occurrence probability.
- Visibility regions are user-defined with a parent tree (defaults: person ⊃
  face ⊃ eyes, upper, lower ⊃ feet, hands). Hiding a region hides its descendants.
- A **basic template** (skeleton partitions in the recommended orders, a few
  example options each, example rules) is available for new recipes and opens
  by default when the owner has none. It is not the deleted 322-item library.
- Each option has English tags (the prompt fragment), a Chinese label, a
  relative weight (> 0), optional conditions and the same effect set as rules
  (see Conflicts).
- Recipes can be created, renamed, edited, duplicated, deleted and exported or
  imported as JSON. They are owner-private.

### Combinations, whitelists and translations (operator, 2026-11-12)
- **Slots**: shared weighted value lists (e.g. colours). An option tag such as
  `{color} china dress` is filled per draw into one tag (`red china dress`, no
  comma). Each option can exclude or only-allow values and reweight them
  (china dress: no green). A drawn value can set state, e.g. to avoid the
  same colour for top and bottom.
- **Only-allow**: an option can restrict a later partition to listed options
  or slot values (school uniform ⇒ bottom only pleated skirt). New skirts
  added later are excluded automatically.
- **Translations**: every tag has a Chinese gloss. It comes from the option's
  own `zh`, the recipe glossary, or the built-in `TAG_ZH` dictionary. Missing
  glosses are highlighted, and the user can type one or look it up through the
  existing Danbooru tag search (`cn_name`). Glosses are display-only, never
  sent and never captioned. They are stored in the recipe and in draw labels.

### Identity, bulk editing and maintainability (operator, 2026-11-12)
- Every partition, option, slot, value, region and rule is referenced by an
  immutable generated id; Chinese names are display labels and can be renamed
  freely without breaking any reference, draw record or filter.
- Option lists support multi-select (also across partitions) and bulk
  add/remove of any effect or condition clause, bulk weight edits, slot
  attachment, move/copy/delete and enable/disable, all with a diff preview
  and undo. 「谁引用了它」 lists and bulk-removes references to an option or
  partition. Deleting a referenced item is blocked or cascades on confirmation.
- Future rule kinds must be addable without changing the engine loop, storage
  or run pipeline. Recipes carry a version with load-time migrations.

### Generation
- The operator sets N (≤ the existing 400-item run cap) and a seed. The same
  recipe, seed and N always produce the same items.
- Options are drawn according to their weights. Coverage of every option is not
  required. Partitions marked "quota" (e.g. framing, subject) distribute N
  proportionally before shuffling, so small runs still match the target shares.
- Drawn items are previewed together with a target-vs-actual share table for
  every option, including how often a partition was skipped because of
  invisibility or conflict.
- Accepted items become ordinary draft entries in the existing list (still
  editable or deletable one by one) and run through the existing durable
  dataset-run, seed, export and caption pipeline.

### Conflicts (the hard part)
Conflicts must be expressed declaratively per option, not as a hand-maintained
pair list. At minimum:
- **Visibility**: framing and view determine which body regions are visible
  (face, upper body, lower body, feet, front/back). A partition or option that
  needs an invisible region is skipped, so an upper-body shot gets no bottoms,
  shoes or leg pose, and a back view gets no expression or eye colour.
- **Resources**: options consume counted capacity. Example: hands = 2, so one
  two-hand action excludes any further hand action, while two one-hand actions
  are allowed. An outfit (uniform, dress) consumes both the top and bottom slots.
- **State requirements**: an option can set a state (pose = sitting, gender =
  female) and others can require or forbid states (crossed legs requires
  sitting or standing; twintails forbids short hair).
- **Explicit exclusions** for anything the above cannot express.
- If no option survives the filters, the partition is skipped and the skip is reported.

### Draw order, conditions and post-draw rules (operator, 2026-11-12)
- **Draw order is independent of prompt order.** A partition that decides
  whether a person exists (e.g. a scene that is no-human) can be drawn first
  while its tags are still emitted last.
- **No-human scenes**: an option can remove the person entirely. Every
  person-dependent partition (subject, appearance, clothing, pose, expression)
  is then skipped as invisible, without per-partition special cases.
- **Unified conditions**: option eligibility uses one boolean condition tree
  (all/any/not over chosen options, state values, region visibility and tags
  already in the prompt). It replaces separate requires/forbids lists and is
  built with dropdowns in the UI.
- **Conditional weights (soft constraints)**: an option's weight can be
  multiplied when a condition holds (e.g. `smile` ×0.5 at night).
- **Post-draw rules** run after all partitions are drawn, so their conditions
  may reference any partition. Effects:
  - `style_add` — tags sent to the provider through the style but **never
    captioned**, so the LoRA absorbs them (e.g. `smile` ⇒ add `gentle smile`).
  - `style_remove` — remove tags from this item's style (e.g. `detailed eyes`
    when eyes are invisible).
  - `content_add` / `remove_tags` — captioned content tags.
- **Removal at three granularities — partition, option, tag** — available as
  an option effect (during drawing) and as a rule effect (after drawing).
  Removing a partition that is not yet drawn skips it. Removing one that was
  already drawn withdraws its tags, refunds its resources and reverts its
  state/visibility effects. Nothing is redrawn. Example: `closed eyes` removes
  the eye-colour partition regardless of draw order.
- **Region-bound style tags**: the recipe can declare that a style tag needs a
  region (`detailed eyes` needs `eyes`). It is then removed from any item where
  that region is invisible (no-human, back view, distant shot).
- The final per-item style = pool style for its ordinal, then removals, then
  additions. It is frozen with the item and copied on re-run. An item whose
  resolved style would be blank is rejected at creation.
- Rule hits are recorded with the draws, so review can filter by them.

### Prompt and caption
- Fragments are joined in a fixed, recipe-defined partition order. Captions stay
  content-only (style is never captioned), so a caption describes exactly what
  was drawn.
- Single-person subject tags (`1girl, solo` / `1boy, solo`) come from the
  subject partition.
- Child safety: if an option tagged as a child can be drawn while the style has
  body-shape or suggestive tags, Start stays blocked, as it does today
  (`CHILD_UNSAFE_STYLE`). Recipe validation also forbids rules that combine
  child subjects with swimwear, underwear, bed or bath options.

### Review filtering
- Each run item stores its draws (partition id, option id and both labels) as
  frozen at creation.
- The training-set thumbnail list (ReviewGrid) can filter by one or more
  partition = option conditions (AND across partitions, OR within one) and shows
  counts per option. It works for runs, re-runs and merged exports alike.
  Legacy items without draws just don't match the draw filters.

## Acceptance Criteria

- [ ] The built-in style prompt library is removed. The style-mode draft starts
      empty or from the selected recipe; character mode is unchanged.
- [ ] Recipes persist server-side per owner (CRUD and import/export); another
      user cannot read or change them.
- [ ] The same recipe, seed and N produce identical items (unit-tested).
- [ ] Weighted shares converge: quota partitions are exact within ±1 item;
      other partitions stay within a statistical tolerance in tests.
- [ ] Visibility: an upper-body or portrait framing never yields
      bottoms/legwear/shoes/leg-pose tags; a back view never yields
      expression/eye tags (property tests over many seeds).
- [ ] Resources: a two-hand action never co-occurs with another hand action,
      two one-hand actions can co-occur, and an outfit never co-occurs with a
      separate top or bottom.
- [ ] State rules hold (e.g. twintails never with short hair).
- [ ] The preview shows target vs actual shares and skip counts.
- [ ] Each run item's draws are stored and returned with the group, and older
      runs without draws still load.
- [ ] The thumbnail list filters by draws and shows per-option counts.
- [ ] A no-human option skips every person-dependent partition and removes
      region-bound style tags such as `detailed eyes` (sent request verified at the fake provider).
- [ ] `smile` ⇒ `style_add gentle smile`: the provider receives it in the style,
      the exported caption contains `smile` but not `gentle smile`.
- [ ] `closed eyes` with `remove_partitions: [eye-color]` yields no eye-colour
      tag whether eye colour is drawn before or after it; withdrawals refund
      resources and are recorded for review filtering.
- [ ] Removing an option/partition by name works during draw and in rules;
      removing a single tag only affects that tag.
- [ ] A `none` option skips its partition, applies its effects, is recorded and
      filterable, and in fill mode stops further draws.
- [ ] Custom regions with parents hide their descendants.
- [ ] The basic template validates and samples n=400 with no overflow and no stale dependencies.
- [ ] `{color} china dress` produces one tag per draw, never `green china dress`
      when green is excluded; slot values are recorded and filterable.
- [ ] School uniform with `allow_options` yields only pleated skirts as bottoms
      in every seed, including skirts added later to the recipe.
- [ ] Missing glosses are highlighted; manual entry and tag-search pick store the
      gloss in the recipe; batch lookup is sequential, abortable and honours 429.
- [ ] Renaming a partition or option changes no reference, run record or filter.
- [ ] Bulk add/remove of an effect on N selected options applies exactly once
      per option (idempotent), previews the diff and is undoable.
- [ ] Deleting a referenced option is blocked unless references are removed too.
- [ ] A frozen v1 recipe fixture still loads after any schema version bump.
- [ ] Draw order ≠ prompt order is honoured; post-draw rules can reference later partitions.
- [ ] Conditional weights shift observed shares as configured (statistical test).
- [ ] Child-safety Start guard still applies, evaluated on every item's resolved style.
- [ ] Backend pytest + Ruff and web lint + build pass. No paid provider calls
      and no reads of real dataset content during development.

## Out of Scope

- Multi-person items and per-person resource allocation.
- Character LoRA mode, reference images and GPT mode libraries.
- LLM-generated options or automatic tag translation beyond the existing `prompt-zh` glossary.
- Retroactively inferring draws for existing runs.
