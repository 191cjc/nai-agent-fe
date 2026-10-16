# Experiment Zero Weight Means Omission

## Request and Boundary

The operator requested: "画风实验中，比重为0代表移除此词条".
The gap is in the exact experiment renderers: they currently emit numeric
zero emphasis. New experiments must omit the selected occurrence at exact
zero, while preserving its index/label/normalized `0.0` in saved weights.
Browser preview and server submission must agree. Ordinary prompt-editor
buttons retain their existing semantics.

Expected production files: web style-experiment.ts, StyleExperiment.tsx and
store.ts (rendering, explanation and empty/length preflight); API style_plan.py
and style_experiments.py (rendering and persisted plan compatibility), and
their existing offline test_style_plan.py/test_style_runs.py regressions.
No dependency, schema, public wire, provider, auth, image-cache or layout work.
No frontend/helper/browser automated tests or paid probes.

## Rendering Contract

- Use scaled integer equality, including signed/decimal zero; no epsilon.
- Select occurrences, never remove duplicate text globally. Keep zero entries
  in the metadata, Cartesian order, total, seed and cursor unchanged.
- Remove an entire selected token, including its outer/nested syntax. Never
  split escaped commas or numeric/bracket scopes. Preserve unselected source.
- Compute nonoverlapping edits against the original source. For contiguous
  zero-tag runs with a following survivor, remove from first removed tag start
  through that survivor's start (remove following separators). For a trailing
  run, remove from preceding survivor's end through last removed tag end.
  Preserve outer whitespace when survivors exist; all tags removed yields
  the empty string. Apply edits/reweights from right to left so offsets stay
  valid. This separator rule must match in both languages.
- Nonzero reweighting and neutral 1.0 unwrapping keep their existing behavior.
- Bound maximum length lazily/conservatively; fixed zero-only dimensions
  shrink the bound. All removed yields a zero style bound. Combined-length
  preflight must handle missing style without subtracting nonexistent outer
  whitespace or reserving a comma for an absent style.
- Preserve GenerationRequest's nonempty base requirement: reject any new
  plan that can remove every style tag while shared prompt is blank, before
  any run or paid work. Determine reachable zero on each exact grid without
  enumerating the product; show an actionable Chinese preflight error.

## Frozen Runs and Compatibility

Persist new run definitions with internal plan_version 2. Existing version1
runs retain their original zero-emphasis rendering and validation after
restart. Keep schema3 and public RunState/OpenAPI unchanged; carry the stored
version internally (for example a Pydantic private attribute) to group
rendering. Do not rewrite stored definitions or replay historical groups.
Same-ID definition checks must continue returning an existing legacy run when
its normalized parameters/ranges match; version alone is not a conflict.
Existing legacy requests that are now invalid under v2 need not bypass the
new public preflight, but GET/Stop/restart of their stored runs must work.

## Execution and Verification

1. Native trellis-implement owns the listed app files/tests. Follow current
   manifests then newest follow-up design; implement directly without nesting
   agents, run lint/types and affected offline backend regressions, freeze.
2. Independent trellis-check reviews full cross-layer behavior and legacy
   restart/idempotency, runs full backend frozen pytest/Ruff/lock/OpenAPI and
   web lint/types, reviews fresh build/staging/activation scripts. Record
   actual evidence in check-zero-weight.md. No browser/frontend/helper tests.
3. Parent owns task/spec sync, explicit env-free locked web build, matched API
   staging and scoped commits (no push/amend). Capture current production
   baseline and private online schema3 backup. Only restart/switch when no
   active paid jobs/runs; preserve config/units/Nginx and private images. If
   activity persists, stage and explain the actual rollout blocker.
4. Verify API-first compatible release, unchanged schema, exact OpenAPI and
   public web hashes, readiness, retained assets and neighboring service.
   Record release/journal, keep broader operator acceptance in progress.
