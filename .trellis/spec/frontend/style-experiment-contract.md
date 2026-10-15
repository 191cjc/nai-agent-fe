# Style Experiment Contract

## Scope / Trigger

Use when changing style experiment helpers, GenerationStore orchestration,
comparison results or the style-heading experiment entry. Experiments are
browser-local sequences of ordinary generation requests, not a new backend
queue or persistent image archive.

## Signatures

- `createStyleExperimentPlan(source, ranges)` validates selected parsed style
  occurrences and independent decimal min/max/step values; returns dimensions
  and an exact `total: bigint` without allocating every combination.
- `styleExperimentCombination(plan, index: bigint)` decodes a zero-based
  mixed-radix ordinal into weighted style text plus labeled weights.
- GenerationStore owns `experiment`, `experimentRunning`, `operationLocked`,
  `startStyleExperiment(source, ranges)`, `stopStyleExperiment()` and
  `clearStyleExperimentResults()`. Components never submit/poll directly.

## Contracts

- Count each axis as floor((max-min)/step)+1 using exact scaled integers.
  Include max only when on the grid; source-order axes, last varies fastest.
  Resolve duplicate tag texts by occurrence/span. Each combination starts
  from the same captured source, replacing selected spans right to left.
  Exact neutral weight 1 uses the shared setter's unwrapped body; keep the
  selected occurrence metadata labeled 1.0. Ranges producing only neutral
  weight must budget their actual compact output in length preflight, including
  a one-value grid whose configured max is above 1 but below the next step.
- Snapshot every validated generation setting, sample_count and native
  character child including x/y at Start. Preserve coordinates through every
  per-step requestFromDraft reconstruction; later marker edits cannot change
  queued combinations. Preserve current draft style/seed. Show total
  groups and total images before starting; never silently truncate the product.
  Expose the frozen per-group count as `experiment.sampleCount`; running
  progress must not recalculate expected image counts from an edited draft.
- Reuse a supplied seed; for null seed, submit null once and latch the first
  generation GET's effective_seed. Every subsequent request uses that seed.
  This is request-level metadata, not a claimed per-image seed contract.
- GenerationStore remains the sole active-operation owner through POST,
  polling, terminal observation and image settlement. Ordinary generation,
  history resume and another experiment must not interleave. Existing
  accepted/first-terminal history notifications retain their meanings.
  `operationLocked` stays true for accepted work whose GET failed until a
  manual recheck settles it; result clearing cannot discard its owner context.
- Fetch and archive a completed group's images before submitting its
  successor. Move URL ownership to its row; internal advancement must not
  revoke archived URLs. Explicit clear, logout/reset and disposal release
  protected rows and all owned URLs. Prevent stale responses/continuations.
  An explicit valid new Start replaces the old archive after all preflight
  validation; disclose replacement in the UI. Ordinary submit and invalid
  Start leave existing comparisons intact.
- Stop prevents future POSTs while allowing an accepted step to settle.
  POST/GET/job/image errors halt progression; no automatic paid retry. A
  manual status recheck may settle an accepted job once, but cannot restart
  a halted experiment. Preserve global uncertain-submit acknowledgement.
- Comparison results render one image at a time in a stable, responsive
  contain-sized area. Traverse archived rows in group order, then their
  images in order. Empty/failed rows contribute one placeholder so metadata
  and errors remain reachable. Show position, group/image identity, weights,
  request/effective seed, task status, parameters and the current download.
  Label positions as results, not image counts when placeholders exist.
- Previous/next arrows sit beside the image area and are disabled at the
  respective boundaries. Left/right keyboard events are handled only inside
  the viewer, excluding editable controls; no global listener. Appending rows
  retains the current selection. Clear/new experiment resets local selection.
  Navigation reads the archive only: no request, draft change, scheduler
  mutation or URL revocation. GenerationStore retains all URL ownership.
  Refresh/closing the page stops future work; existing parameter history
  remains durable, experiment grouping does not.

## Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| No selected safe occurrence / stale source | Reject before POST; request current selection |
| Duplicate selection / unknown or legacy syntax | Reject or disallow selection; preserve original text |
| Empty/non-decimal input, step <= 0, min > max | Visible validation error; no POST |
| max not on step grid | Use only grid points <= max; no extra endpoint |
| Invalid generation/model/length | Reject before paid submission; no silent coercion |
| Empty seed | First request null, later use first observed effective_seed |
| First GET fails before seed known | Halt with accepted id; no second random POST |
| Stop during POST/poll/images | Latch; accepted step may settle, successor blocked |
| Job/image/transport failure | Preserve rows, halt remaining combinations |
| Uncertain POST | Preserve existing global uncertainty lock; never auto resend |
| Logout/disposal during a run | Invalidate owner token, stop futures, clear protected URLs/state |
| First/last retained result | Disable previous/next respectively; do not wrap |
| Failed/empty group | One navigable placeholder with its metadata/errors |
| More archived rows arrive while browsing | Retain the selected group/image |
| Clear/new experiment | Reset viewer position; store owns URL cleanup |

## Good / Base / Bad Cases

- Good: two three-value ranges generate nine distinct groups with fixed base
  request and seed. Base: min=max produces one group. Negative/zero weights
  follow the same exact decimal arithmetic as ordinary numeric weight edits.
- Good: 0.8..1.1 by 0.2 gives 0.8 and 1.0, with no floating-point noise.
- Good: two images in group 1 precede group 2's placeholder, then group 3's
  images. Base: one image disables both arrows. Bad: an append selects the
  newest image or a global direction-key listener interrupts prompt editing.
- Bad: Cartesian diagonal only, random seed on every request, float loops,
  starting the next POST from onTerminal before images load, or revoking an
  archived group's images while advancing.

## Verification Required

Respect the retained operator restriction: no frontend automated tests or
browser automation. Run ESLint/TypeScript, source-review the full lifecycle
and range boundaries, and build explicit inputs in a fresh env-free stage.
Review Stop during all phases, repeated terminal/status checks, logout with
pending POST, source edits, image ownership and ordinary-generation guards.
Review shrinking neutral replacements across multiple selected occurrences
and near-limit neutral-only grids, including an off-grid configured maximum.
No paid experiment may be executed as an implementation check.
Source-review single/multi-image ordering, placeholder errors, selected
metadata/download consistency, first/last arrows, viewer-only keyboard scope,
append stability, reset/logout, contained responsive sizing and unchanged
ordinary results. Distinguish static review from operator browser acceptance.

## Wrong vs Correct

- Wrong: React effects start generation requests, selection is keyed by tag
  text, or a failed request is automatically resent.
- Correct: explicit Start invokes GenerationStore; immutable occurrence-based
  plans drive one guarded submission at a time, stopping on ambiguity/failure.
