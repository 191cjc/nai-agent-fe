# Style Experiment Contract

## Scope / Trigger

Use for exact weight previews, batch creation/observation/Stop, reattachment or
saved comparisons. Experiments are server-owned durable runs. Browser close,
refresh, logout and connection failure detach observation, not server work.
See backend/durable-experiment-contract.md for the owning API/schema contract.

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
  for its 32-entry/64-MiB in-page cache and metadata/expiry/URL lifecycle.

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
- Authentication entry checks for an active run and attaches via GET without
  changing the draft. Preserve separately guarded latest-history restoration.
  An unresolved active check/creation or attached running/stopping state blocks
  overlapping new ordinary/batch submissions locally. Backend also enforces
  at most one active run per owner.
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
  prefetch or accumulate entire run Blobs. Metadata/parameters outlive seven-day
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
  a new session/draft. Bad: navigation loads an entire experiment into memory.

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
