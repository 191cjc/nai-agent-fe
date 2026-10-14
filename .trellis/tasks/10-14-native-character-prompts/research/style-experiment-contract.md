# Research: Style experiment enumeration and generation lifecycle

- Query: How can the style editor exhaustively vary selected tag weights while preserving existing generation, authentication, history and transient-image contracts?
- Scope: mixed — local frontend/backend sources and specs; public pinned upstream source only.
- Date: 2026-10-14

## Findings

### Recommended boundary

This can remain a frontend-only feature. The existing API accepts every
combination as a normal `GenerationRequest`; saved parameters already retain
the weighted style string. Keep **GenerationStore as the sole owner of paid
POSTs, job polling, the active job and image retrieval**. A React experiment
panel should only configure a run and render its observable progress/results.
Do not give that panel its own API calls, polling effect or image URLs.

The main session decided to preserve **draft.sample_count**, along with all
other settings, in the experiment snapshot. Each combination is one existing
generation task returning that many images. Preview `combination count ×
sample_count` before the explicit Start click. Do not silently force one image
or claim per-image seed metadata.

### Files found / affected paths

| File | Role / minimal change |
| --- | --- |
| `apps/web/src/App.tsx:75` | Editor heading and ordinary submit controls; place experiment button beside style label at `:105`. |
| `apps/web/src/App.tsx:226` | Current result display and close action; add a comparison gallery or separate component without double URL ownership. |
| `apps/web/src/App.tsx:339` | History reuse/resume controls; keep resume mutually exclusive with batch ownership. |
| `apps/web/src/App.tsx:413` | Existing outcome-uncertain acknowledgement UI; retain this protection for batch POST failure. |
| `apps/web/src/store.ts:66` | `requestFromDraft` validates and snapshots all generation parameters, including native character boundaries. |
| `apps/web/src/store.ts:185` | GenerationStore owns the needed run state machine and archive lifecycle. |
| `apps/web/src/store.ts:608` | AppStore wires accepted/terminal history notifications and logout/reset/dispose. |
| `apps/web/src/prompt-weights.ts:17` | Parsed tags expose original source spans, text, numeric weight and numeric-prefix span. |
| `apps/web/src/prompt-weights.ts:46` | Exact BigInt decimal arithmetic exists privately; share/extract it rather than introduce floating point ranges. |
| `apps/web/src/prompt-weights.ts:159` | Existing selected-span weight adjustment; add an absolute-weight counterpart or reuse a common replacement primitive. |
| `apps/web/src/PromptEditor.tsx:16` | Existing source-derived tag view; should retain its current blur/manual edit behavior. |
| `apps/web/src/styles.css` | Experiment configuration and responsive labeled comparison display. |
| `apps/web/src/api.ts:199` | Existing typed submit/generation/image methods suffice; no wire change required. |
| `apps/api/src/novelai_api/generations.py:296` | Existing sequential provider scheduler and random effective-seed assignment. Research only; no backend edit needed. |
| `apps/api/src/novelai_api/mcp_images.py:216` | Adapter forwards seed, n_samples and weighted base prompt unchanged. |

Useful separation is a pure `style-experiment.ts` for validated range/count,
lazy combination index decoding and source replacement, plus a small
`StyleExperiment.tsx` UI. Keep operation orchestration in GenerationStore.

### Existing backend behavior and limits

- `generations.py:307`: a process-wide semaphore permits three accepted
  jobs, including the running job; `:313` uses one worker. It is **not** three
  concurrent image generations or a per-user queue.
- `app.py:277`: full local queue returns `429 queue_full`; provider absence
  returns `503 provider_unavailable`. There is no separate generation
  per-minute limiter in this route. Upstream paid-call `429` becomes terminal
  `provider_rate_limited` (`mcp_images.py:301`). Never automatically retry it.
- `generations.py:326`: a blank seed is randomized once before saving and
  enqueueing. Non-null seeds are preserved. The stored `parameters.seed` and
  `effective_seed` therefore match even when the submitted seed was null.
- `api.ts:49` / `app.py:282`: acceptance returns **id/status only**. Obtain
  `effective_seed` from the first successful GET, which may still be queued
  or running. All later combinations use that seed; leave the editable draft
  seed unchanged. If the first job/GET fails, do not submit an independently
  randomized second job.
- `mcp_images.py:225`: sample_count maps directly to `n_samples`, with one
  seed per request. The API has no seed for each returned image. Index labels
  are return-order labels only.
- `generations.py:20`: limits are 8 MiB per image, 32 MiB per task, 64 MiB
  process-wide cache and ten-minute TTL (`:23`). Later tasks can evict older
  cache entries before that TTL. Fetch each successful task's images before
  starting its successor if comparisons must retain earlier results.
- Parameter history is durable; experiment grouping, progress and image
  comparisons would be browser-memory-only. Reload cannot recover an
  experiment automatically; individual task parameters remain in history.
- No cancellation endpoint exists. Stop can prevent future submissions but
  cannot cancel or refund an accepted job.

### Exact decimal ranges and lazy Cartesian enumeration

- Accept ordinary signed decimal syntax consistent with the weight parser;
  reject exponents, NaN, infinity, empty inputs, zero/negative steps and
  min > max. Do not invent an upstream weight range or clamp silently.
- Configure min/max/step independently for each chosen occurrence. Normalize
  that occurrence's min/max/step to a common decimal scale using BigInt units.
  Its per-tag count is `floor((maxUnits-minUnits)/stepUnits)+1`. Generate
  `minUnits + i*stepUnits`; include max only if reached exactly. Never append
  an extra off-step max. For example 0.8..1.1 by 0.2 gives 0.8, 1.0.
- With k chosen tags having n_i values each, count is `product(n_i)` using
  BigInt, before allocating results or making a request. Do not build arrays
  of every value or every combination. Decode one ordinal by mixed-radix
  division/remainders, with the last selected tag varying fastest, to produce
  deterministic ascending nested-loop order.
- The UI must show total groups and total images. If the product exceeds an
  implementation/resource policy, reject before starting with an explicit
  reason; never silently truncate a request for all combinations. A lazy
  iterator avoids eager allocation but does not bound retained images.
- Reuse existing decimal parse/format helpers from prompt-weights. Avoid
  Number arithmetic for weight increments or count products. Convert only a
  policy-bounded combination/result ordinal for ordinary array indexing.
- Tags with `weight === null` are visible but unavailable for experimental
  weighting; preserve their source. Existing complex/incomplete/legacy
  emphasis must not be reinterpreted.
- Select occurrences by original source span, **not text**: duplicate text
  may occur multiple times. Capture the entire original style source and
  validate selected spans against it at Start; rebase/clear selections when
  current draft style changes while configuring.
- Every combination starts from that same captured style source. Replace
  selected original spans from right to left so earlier offsets do not shift.
  For existing numeric groups replace only weightRange; for plain safe tags
  wrap the source in `weight::original::`. Preserve whitespace, separators,
  escaped commas, siblings and native character text exactly.
- Validate the final style and combined style/shared length through existing
  limits. Prefer a bounded worst-case preflight so a later longer numeric
  value cannot discover invalid input after earlier paid jobs have run.

### Minimal GenerationStore run state machine

Recommended conceptual fields (names can vary):

- `experiment`: configuration snapshot, selected source spans/range,
  immutable validated base request, total, nextOrdinal, effectiveSeed,
  status and stopRequested.
- `experimentResults`: completed/failed observed tasks labeled with ordinal,
  exact tag weights, accepted id, effective seed, task status/error, images
  and image warning. Store rows only for attempted jobs, not pending product.
- one existing active job (`job`, `activeId`, controller, timer) plus a
  private operation/run token that outlives the terminal image fetch.

Useful public commands are `startExperiment(config)`, `stopExperiment()` and
`clearExperimentResults()`. Useful private primitives are
`submitParameters(parameters)`, `observeActiveJob(...)`,
`finishExperimentStep(job, operationToken)` and `advanceExperiment(...)`.
Refactoring ordinary submit to `submitParameters` avoids duplicating paid
request uncertainty handling. Only the orchestrator may call that primitive.
Keep one internal active-operation token covering POST, polling and image
settlement; ordinary submit can use it too. `clearResult()` must invalidate
the run/continuation token as well as its existing epoch/timer/controller,
so any caller (including dispose) prevents later batch submissions. A private
per-step cleanup can clear the active result without invalidating the overall
run when advancing deliberately.

Transitions:

1. **idle/completed/stopped → running**: validate config, selected source,
   model weight compatibility and snapshot `requestFromDraft(draft)` once;
   explicitly deep-copy native character children. Preserve sample_count,
   quality, model, sampler, dimensions, steps, CFG, shared/negative prompts.
   Later editor/settings/history changes must not affect this snapshot.
2. **running → submitting → polling**: submit exactly one generated request;
   retain active ownership through the first GET. Fixed seed starts known;
   null seed is captured from first successful GET.
3. **polling → terminal/image retrieval → archive → next**: notify history
   on first terminal observation as today, fetch images, archive result and
   transfer URL ownership, then submit the next ordinal only if the same
   epoch/run token remains active and Stop has not been requested.
4. **stop requested**: latch immediately. Finish observing any pending POST
   or accepted job, fetch/archive its result, then mark stopped. Do not start
   a successor, even if Stop occurred just after terminal status was seen.
5. **GET error**: pause with the same accepted id and allow explicit Check
   Status, never re-POST that combination. A manual recheck may recover the
   current task but must not duplicate archiving or successor submission.
6. **task failed / POST rejected / image retrieval failure**: safest MVP is
   halt remaining combinations with clear reason and keep previous rows.
   Missing/expired images are distinct from failed generation. The main
   session can choose continuation for missing images explicitly; it must
   never hide those rows or retry paid work automatically.
7. **POST uncertain**: halt the batch, retain global submitUncertain and
   existing Check History/acknowledgement flow. Acknowledgement does not
   automatically restart the batch or resend the failed ordinal.
8. **logout/dispose**: stop the batch before clearing timers/results;
   invalidate epoch and run token. Logout with pending POST remains
   outcome-uncertain if logout itself fails. Failed logout must never resume
   the paid sequence. Successful logout/401 resets all protected rows/URLs.

### Critical existing timing and ownership hazards

- `store.ts:323–334`: onTerminal fires before loadImages. It is intentionally
  a history synchronization notification, **not a batch-completion hook**.
  Starting the next job there would clearResult/revoke old images before
  retrieval, overwrite the controller and potentially mix images between jobs.
- `store.ts:327`: checking becomes false and activeId becomes null before
  loadImages finishes. Guard ordinary submit, history resume, result close
  and new batch start with run/operation ownership through retrieval, not
  only busy/activeId/checking. A hidden panel is not a lifecycle boundary.
- `store.ts:350`: loadImages runs concurrent image requests, then performs an
  epoch check before creating object URLs. Preserve this sequence. A run
  cancellation must invalidate it so a stale response cannot add protected
  images or start another paid task.
- `store.ts:348`: missing-image deduplication is by image index only and
  assumes images belongs to one job. Archive/empty active images before
  starting another; do not put all batch images into this existing flat list.
- `store.ts:369`: clearResult revokes every currently active image. Moving
  completed images to an archive requires ownership transfer: archive gets
  the URL array and active images becomes empty without revoking those URLs.
  Exactly one owner revokes each URL on archive clear, reset, logout and
  dispose. Do not have active/archive arrays both treat the same URL as owned.
- Existing terminal deduplication compares prior job id/status. Retain it for
  history notifications and add separate per-batch-step completion/advance
  deduplication; manual refresh of terminal tasks must not append twice or
  submit another successor.
- Ordinary draft reuse can remain editable during a run if the snapshot is
  immutable, but history **resume** must be disabled/guarded during it.
  `AppStore.dispose()` currently only clearResult+tags reset (`:628`); extend
  the generation cleanup to release retained experiment URLs too.
- Retaining every source blob/object URL may exhaust memory on a large
  Cartesian product. Choose and disclose a finite preflight run/image limit
  or a finite preview retention policy. If previews are evicted, keep all
  attempted task metadata/weight labels and say when an image was removed.
  No image persistence in Web Storage, IndexedDB or server history is
  authorized by the existing contract.

### External references (public source, no provider call)

Pinned upstream source commit: `49554a12938ed33856dbd8a9ce11db5f41704123`
(public main/package 0.5.1 as recorded by preceding provider research).

- [generate.py lines 75–76, 120–121](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/tools/generate.py#L75-L76): one seed and n_samples forwarded into one request.
- [payload.py lines 105–112](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/nai/payload.py#L105-L112): n_samples and seed serialized directly. No additional seed derivation is established by this serializer.
- `research/deployed-mcp-schema.json`: pre-existing non-billable schema
  artifact, seed integer/n_samples integer; no per-image seed contract.

These were source reads with Python urllib and bounded timeouts; no secrets,
production endpoints, browsers, providers or paid tools were accessed.

### Related specs / verification

- `.trellis/spec/frontend/workspace-contract.md`: single source of draft
  strings; logout epoch/uncertainty; terminal history synchronization before
  image loading; transient image ownership; no frontend/browser tests.
- `.trellis/spec/backend/native-character-contract.md`: keep style/shared/
  characters distinct, source bounds and compatible structured model IDs.
- `.trellis/spec/backend/api-contract.md`: accepted id only, job success
  distinct from accepted submission, parameter-only history and typed errors.
- `.trellis/spec/backend/provider-adapter-contract.md`: no automatic retries
  and no invented upstream contracts from UI names (tag adapter scope).
- Allowed verification: source review of enumeration/lifecycle/races, ESLint,
  TypeScript and fresh environment-free production build. No frontend test
  files, browser automation or paid experimentation calls.

## Caveats / Not Found

- Per-image seeds and cross-image-index determinism are not represented in
  the browser API and were not verified upstream. Shared effective_seed is
  a request-level guarantee; do not label every sample with a claimed exact
  individual seed.
- No backend batch cancellation, durable batch grouping/resume, image archive
  or provider pricing endpoint exists. Do not promise those outcomes.
- Numerical weight support is documented as V4+; an unknown/legacy model must
  not silently receive newly synthesized numerical emphasis. The verified
  native model list is a conservative supported experiment subset.
- UI configuration cardinality, image retention cap and missing-image
  continuation are implementation/product policies, not provider limits.
