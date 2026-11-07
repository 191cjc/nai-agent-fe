# Style Experiment Contract

## Scope / Trigger

Use for exact weight previews, batch creation/observation/Stop, reattachment or
saved comparisons. Experiments are server-owned durable runs. Browser close,
refresh, logout and connection failure detach observation, not server work.
See backend/durable-experiment-contract.md for the owning API/schema contract.
Dataset runs reuse StyleRunStore (`startDataset`, `kind`) and every rule
below; see backend/dataset-run-contract.md.

Whole-line per-tag comments and raw/effective projections follow
[Individual Hidden Tags](../backend/prompt-comments-contract.md). Syntax is opt-in per frozen request;
absent/false preserves the legacy contracts below.

## Signatures

- createStyleExperimentPlan(source, ranges) validates occurrence-based decimal
  ranges and computes exact total: bigint without allocating combinations.
- styleExperimentCombination(plan, index: bigint) remains an exact renderer;
  the browser must never use it to schedule paid per-group submissions.
- WorkspaceApi wraps POST /api/style-experiment-runs, GET /active,
  GET /{id} and POST /{id}/stop. Components delegate to stores.
- SavedResultsStore owns paginated /api/style-experiments metadata and lazy
  authenticated PNGs, independently of the run. Follow viewer-cache-contract.md
  for its default32-entry/64-MiB in-page cache, explicit256-entry/256-MiB
  preload mode and metadata/expiry/URL lifecycle.

## Contracts

- Exact scaled-integer counts: floor((max-min)/step)+1; source-order axes,
  last varies fastest. Include max only on the grid. Select duplicate text by
  occurrence; preserve unselected/unsupported syntax. Neutral 1.0 unwraps only
  its outer numeric emphasis. For new experiments, exact 0 omits the selected
  occurrence while retaining its index/label/normalized `0.0` in metadata.
  Preserve unselected duplicate text. Ordinary prompt buttons keep numeric
  zero emphasis. Preview maximum rendered length conservatively, including
  single neutral/zero grids with off-grid maximum. No hidden truncation.
- Zero omission uses original nonoverlapping spans: a contiguous removed run
  with a following survivor removes through that survivor's start; a trailing
  run removes from the previous survivor's end through its own last tag end.
  Preserve outer whitespace if any tag survives; all removed yields `''`.
  Apply deletions and surviving weight replacements from right to left.
  Respect parsed escapes/bracket/numeric scopes; never split raw commas.
- Before Start, reject any plan whose exact grids can simultaneously remove
  every style tag when shared prompt is blank. Show an actionable error to
  add shared content. Keep zero-only length bounds nonnegative and exclude
  the style/shared comma when style is absent. No paid group may strand on
  an empty base. Stored version1 runs retain server-side original semantics;
  the current explanatory zero-omission rule applies to newly created runs.
- Start validates every setting/metadata bound, freezes source/ranges and the
  native character coordinates/sample count, generates one UUID and issues one
  create POST. The server derives all groups. Show total groups/images before
  starting and use the server snapshot for running/reconnected displays.
- Server chooses one seed once if blank; every group uses it even if the first
  fails. Never infer a new seed from draft edits, image availability or GETs.
- Authentication entry reads the owner's run queue
  (`GET /api/style-experiment-runs/queue`) and attaches without changing the
  draft. Preserve separately guarded latest-history restoration. An unresolved
  queue check or create blocks new batch submissions; running runs do not — a
  new experiment/training set is added to the queue ("加入队列"). Unfinished runs
  still block ordinary generation locally. The progress area lists every
  unfinished run (badge, name, lane, 生成中 / 排队中 N, own Stop) plus runs that
  finished while observed until dismissed; saved-set delete is disabled for
  every unfinished run.
- Failed groups advance automatically. Show processed/success/failure counts
  and safe errors, including completion with failures. A disconnected poll is
  an observation error, not a stopped run. Offer reconnect/retry read actions.
- A lost create response reconciles only with known UUID GET; never auto resend
  POST. An immediate GET404 cannot prove a still-pending POST was not accepted.
  Preserve uncertainty until reconciled or explicitly acknowledged, with no
  automatic paid retry. Keep ordinary generation's separate safeguards.
- Explicit Stop POST prevents new server groups; accepted current group may
  settle. Keep Stop reachable after reentry even when configuration is closed.
  Lost Stop responses are not evidence of stopping; reconcile/read/show errors.
- Reset/logout/session expiry/dispose abort observers, invalidate epochs and
  revoke owned Blob URLs. They never call Stop. Stale create/poll/Stop responses
  cannot attach to a later login or mutate another run. Failed logout must
  leave the authenticated user able to reattach.
- GenerationDraft and ordinary history reuse exclude experiment metadata.
  Observation/saved viewing never mutates draft or a normal generation owner.
- Use independent lazy comparison for server runs, while active and terminal.
  Read bounded group metadata, load only the current PNG on a cache miss; never
  automatically prefetch or accumulate entire run Blobs. The explicit
  experiment-viewer preload action is the bounded exception described in
  viewer-cache-contract.md. Metadata/parameters outlive seven-day
  images; cached PNGs retain their original expiry. Explicit refresh may
  discover later groups; retain the selected group/image when possible.
- Left/right order traverses group images then the next saved group. Failed,
  empty and expired groups contribute a navigable placeholder with their
  weights/seed/status/parameters. Show position, identity, expiry and current
  download. Stable contain sizing; arrows disable at boundaries. Direction keys
  act only inside the viewer and exclude editable controls, never globally.
- Viewer selection/session races are guarded; replacement/close/logout/dispose
  revoke only that viewer's URLs. Clearing comparison affects the page only,
  not server records, server progress or image retention.

## Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Stale/unsafe/duplicate selected occurrence | Reject before create; preserve original source |
| Invalid decimal, step<=0, min>max or over-bound plan | Visible preflight error; no POST |
| All style tags can reach zero and shared is blank | Ask for shared prompt before POST |
| Selected occurrence is exact zero | Omit it; keep `0.0` comparison metadata |
| Valid explicit Start | One creation POST, then read-only polling |
| First group fails with blank requested seed | Later groups use same server seed |
| Group/provider/image display error | Record/show error; server continues later groups |
| Lost create response | Known-id GET reconciliation; no automatic POST retry |
| Poll failure | Visible disconnected state/reconnect; server continues |
| Explicit Stop | Stopping/stopped from server; current accepted group may finish |
| Reload/logout/dispose | Detach only; entry GET reconnects same active run |
| Foreign/stale run/session response | Cannot change current user's state |
| Failed/expired group | Navigable metadata placeholder |
| Clear current comparison | Release local viewer URLs only |

## Good / Base / Bad Cases

- Good: 0.8..1.1 by 0.2 yields 0.8 and 1.0 exactly. Two three-value dimensions
  produce nine combinations with one frozen request seed/settings snapshot.
- Good: group 2 fails while the page is closed; entry attaches to group 7 and
  history can compare earlier retained images with left/right arrows.
- Base: one-value grid executes once; one saved image disables both arrows.
- Good: `artist:a, artist:a, scene`, selecting only occurrence 1 at zero,
  renders `artist:a, scene`; metadata still identifies removed occurrence 1.
- Base: one style tag at zero and shared `scene` renders an empty style and
  submits base `scene`. Signed `-0.000` has the same behavior.
- Bad: an effect resubmits paid groups after reconnect, or a late GET overrides
  a new session/draft. Bad: navigation implicitly loads an entire experiment
  or explicit preloading evicts earlier images while reporting all as cached.

## Verification Required

Respect operator restriction: no frontend/helper automated tests or browser
work. Use ESLint/TypeScript, full source review and a fresh explicit env-free
build. Review entry/failed entry, creation ambiguity, active conflict, first
failure/seed, Stop races, disconnected polls, current/terminal comparison,
logout success/failure, stale session responses, draft/coordinate edits and
URL cleanup. Backend uses meaningful fake-only scheduler/parser regressions.
Real interaction/paid results remain a separate operator acceptance gate.
For zero omission, inspect shared backend golden vectors for edge/adjacent/all
removals, grouped/escaped separators, duplicate occurrences, nonzero neighbors,
zero reachability and near-limit bounds; do not run frontend helper tests.

## Wrong vs Correct

- Wrong: browser lifetime owns the paid loop or disconnection means stopped.
- Correct: explicit Start creates a durable server run; browser reads progress,
  compares saved images and sends Stop only when the user chooses it.

## Built-in face close-up category (2026-11-06)

- Style dataset library category `face` (脸部特写, 24 items, default-selected like every
  library item) sits after `portrait`. Ids are positional per category
  (`face-N`), so adding a category never renumbers existing items. Every item keeps
  hair, eye colour and coloured clothing tags and has a `TAG_ZH` gloss for each tag.
  Purpose: large faces in the set so style LoRAs learn eye/face rendering.

## Review grid multi-select re-run (2026-11-06)

- Every tile (including failed groups without an image) has a top-left select toggle;
  clicking the image also toggles selection (never discard — accidental clicks
  discarded images). Discard/restore is only the dedicated top-right ⊘ / ↶ button
  beside 「查看原图」. Selection is a Set of tile keys
  (`<job>:<index>` / `<job>:x`) held in ReviewGrid state, so it survives paging,
  category and hide-discarded filters; a reload keeps only keys that still exist.
- Quick picks: all failed groups not yet re-run; discarded images not yet replaced
  (per group, discarded count minus existing re-runs minus sources still queued in
  this set's unfinished re-run batches); this page; the whole current filter (all
  pages); clear. Quick picks never select already-replaced or already-queued items.
- 「重跑所选」 opens the batch editor for the selected tiles: one optional new style,
  per-tile prompt edits, and 「开始重跑某张时弃置被替换的原图」 (default on; sends
  `discard_index` only for kept succeeded images). Rows flag failed / discarded /
  already re-run N times / queued N.
- Submission (2026-11-06, replaces the browser loop): one
  `POST /api/rerun-batches` creates a durable server-side batch (see backend
  dataset-run-contract 「Durable re-run batches」); the page may close afterwards.
  The batch id is generated when the editor opens and reused after an unknown
  outcome (idempotent); a definite 4xx refusal draws a new id. Accepted tiles are
  deselected and the run is handed to `StyleRunStore.track` so it shows in the
  queue panel at once.
- Queue panel: kind `rerun` rows show badge 「重跑」, unit 张, 「查看已保存结果」 opens
  the source training set, stopped batches offer 「继续剩余 N 张」. While a batch is
  unfinished its training set counts as active (cannot be deleted from the list).

## Per-image Chinese gloss of training prompts (2026-11-06)

- The saved-result viewer shows 「中文：…」 under each training-set image's prompt
  (scene plus every person) and 「画风中文：…」 when any style tag has a gloss; the review
  grid shows a two-line gloss under each tile (full English + Chinese on hover).
- Glosses come from the `TAG_ZH` dictionary (`translatePrompt`): each comma tag is
  looked up; unknown tags stay as written, so custom prompts are glossed tag by tag.
- `PromptGloss.tsx` is loaded through `dataset-lazy.ts`; the gloss table stays out of
  the main bundle (its own `prompt-zh` chunk).
- 2026-11-06: `TAG_ZH` expanded 1113 → 2998 entries with the most-used Danbooru
  general tags (WD tagger `selected_tags.csv`, category 0, by count), excluding
  explicit sexual/genital tags and non-word tags; keys sorted case-insensitively.
  Built-in style and character library tags remain 100% glossed.

## Training-caption edits (2026-11-06)

- Saved viewer, training-set groups: 「训练词（导出 caption）」 line with 「已修改」
  badge, 「修改训练词」 (lazy `CaptionEditor`) and 「恢复默认」. Only the export
  changes; nothing is generated.
- Review grid 「批量改训练词」: scope 已选 / 当前筛选 / 全部 (succeeded groups only),
  operation 文本替换 (case-sensitive, all occurrences; empty replacement deletes) /
  加前缀 / 加后缀 / 恢复默认 (`applyCaptionOperation`); preview of the change count and
  three samples; results that would be blank are skipped. Saved in ≤3000-item chunks
  via the captions PUT; tiles show 「训练词已改」 and gloss the override.

## Review grid search and re-run bulk edits (2026-11-07)

- 「搜索训练词」 filters tiles together with category and hide-discarded. Text searched
  per group (precomputed once per load): `contentCaption()` (override, else derived
  tags) plus its Chinese gloss, lower-cased. `parseSearch`: terms split on `,`/`，`, all
  must match as substrings; `-term` excludes. While searching the quick pick reads
  「选择搜索结果（N）」 plus 「取消选择搜索结果」; selection still survives search changes.
- Re-run editor: multi-person tiles show the scene box plus one box per person
  (「人物 N（位置不变）」); changed people are sent as `characters` (all people, in
  order). A bulk bar applies 文本替换 / 加前缀 / 加后缀 (`applyRerunOperation`, reusing
  `applyCaptionOperation`) to every prompt in the batch, scoped 场景和人物 / 只改场景 /
  只改人物 when any multi-person tile is present; results that would be blank are
  skipped and counted. It edits the drafts only; nothing is sent until 「加入队列」.
- `applyCaptionOperation` also collapses empty tags left by a removal (`a, , b` → `a, b`).
