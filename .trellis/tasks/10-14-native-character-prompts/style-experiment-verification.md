# Style Experiment: Independent Full-Scope Review

- Date: 2026-10-14
- Reviewer: dispatched `trellis-check` agent
- Source scope: `style-experiment.ts`, `prompt-weights.ts`, `store.ts`,
  `StyleExperiment.tsx`, `App.tsx`, and `styles.css`, including the prior prompt
  editor and native-character integration paths.
- Result: no concrete defects found; no source fixes were needed.

## Static Verification

- `cd apps/web && npm run lint`: passed. The script runs ESLint followed by
  `tsc --noEmit`; both passed.
- `git diff --check`: passed.
- No frontend automated tests, test scripts, browser automation, paid image
  or advice calls, credential reads, or production mutations were performed.
- The main session owns the subsequent fresh, explicit-input environment-free
  production build and web-only publication. Those are not claimed here.

## Source Review Evidence

### Exact Enumeration and Prompt Preservation

- Decimal parsing, normalized rendering and arithmetic use scaled `bigint`
  units. Invalid decimal syntax, zero/negative steps and inverted bounds are
  rejected before submission.
- Each dimension uses `floor((max-min)/step)+1`; a maximum outside the grid is
  not appended. Source-traced examples include `0.8..1.1` by `0.2` (two
  values), equal endpoints (one value), negative ranges and crossing zero.
- Axis counts/products stay `bigint`. Only one ordinal is decoded through
  division and remainders; no array of future values, combinations or results
  is allocated. The last source occurrence varies fastest, so two independent
  three-value axes address all nine combinations rather than a diagonal.
- Selection uses occurrence indexes checked against the captured parsed
  source, including duplicate tag text. Descending-span replacement always
  starts from that captured source; numeric groups change only their prefix,
  while safe plain tags retain their bodies and original separators.
- The maximum weighted length is bounded from the largest endpoint magnitude,
  common emission precision and possible negative sign. Both individual style
  length and trimmed style/shared composition are checked before Start;
  every actual variant also passes the existing request validator.

### Snapshot, Seeds and Operation Ownership

- Start validates before clearing previous comparisons. It freezes all
  validated scalar/string settings and separately copies/freezes native
  character children. `sampleCount` exposed by the run is captured at Start.
  Live draft edits/reuse cannot alter outgoing experiment parameters.
- Fixed seeds are copied unchanged. An empty seed is submitted as null once;
  the first successful generation GET latches `effective_seed`, including
  queued/running observations. Advancement refuses a second unknown seed.
- `submitParameters` remains the only generation POST path. The operation
  reservation spans POST, polling, terminal observation and all image
  settlement. Ordinary submit, history resume and another experiment cannot
  interleave with it or the guarded inter-step timer gap.
- Accepted and first-terminal notifications retain history-only behavior.
  Advancement occurs after image settlement and archive transfer, never in
  the notification callbacks or React effects.

### Stop, Failure and Manual Recheck

- Stop during POST, polling or image retrieval latches `stopping`; the current
  accepted task can finish and archive, with no successor. Stop during the
  zero-delay gap clears the continuation and leaves the run stopped.
- POST rejection/uncertainty, GET errors, failed jobs and missing/failed
  images halt progression without automatically sending another POST.
  Uncertain submissions retain the global history/acknowledgement lock.
- A GET error retains its accepted operation and id, including when a run is
  already marked failed. Clear/new generation/resume remain blocked until
  explicit status rechecking settles the accepted task. Recovered polling
  may finish that same task, but the failed run cannot resume its sequence.
- Terminal notification and archive guards prevent repeated terminal checks
  from duplicating history refresh, comparison rows or successor requests.

### Image Lifetime and Protected-State Cleanup

- Image fetches settle before object URLs are created; stale epoch/operation
  responses cannot publish images. Partial URL-creation failure revokes URLs
  created by that failed attempt.
- Archive insertion transfers the active image array, then replaces the
  active slot without revocation. Internal advancement only clears active
  resources. Later ordinary generation retains prior comparisons.
- Explicit comparison clear/replacement, logout/reset and disposal revoke
  archived URLs. Logout/disposal invalidate epoch and run continuation state;
  stale POST/poll/image callbacks cannot advance. Logout while POST is pending
  preserves uncertain outcome protection if logout fails.

### UI and Existing Editor Integration

- The style-heading control opens a mounted configuration panel. Hidden
  positive/negative content and folded configuration preserve state. Style
  source changes invalidate occurrence selections before Start.
- Per-occurrence inputs are labeled; unknown/legacy syntax is visible but
  unavailable for automatic weighting. Configuration input Enter is prevented
  from submitting the outer ordinary-generation form.
- Running configuration uses its captured source/ranges/sample count.
  Progress and Stop remain visible outside the folded configuration and
  negative prompt tab. The preview discloses groups and total requested images.
- Comparison rendering is paged, with ordinal, varied weights, request seed,
  status, image errors and download links. Archived experiment jobs are hidden
  from the ordinary result slot; subsequent ordinary results still render.
- Existing manual-only prompt edit entry, exact 0.1 buttons, stable character
  identities, explicit tag targets, history reuse and negative side-tab layout
  remain intact by source inspection.

## Remaining Acceptance

Operator desktop/mobile/keyboard interaction and actual-provider output remain
unverified, as required by the testing restrictions. Source review and static
checks do not establish browser behavior or successful paid-provider output.
The experiment is intentionally browser-memory-only, retaining produced images
until explicit clear/replacement or protected-state cleanup; refreshing does
not restore the sequence or comparison grouping.

Source ownership is handed back to the main session. No reviewer source edits
remain in flight.
