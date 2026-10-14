# Design: Style Experiment

## Change Boundary

The existing generation workspace can run only one draft request. Add lazy
style-weight enumeration and a browser-local sequential experiment using the
existing generation service. GenerationStore remains the only submission,
polling and image owner; UI configures commands and renders state.

Source changes: `style-experiment.ts` (pure exact ranges/combination indexing),
`prompt-weights.ts` (share exact decimals and absolute span replacement),
`store.ts` (immutable run snapshot, sequence and archive lifecycle),
`StyleExperiment.tsx` (configuration/progress/comparison), `App.tsx` (heading
entry and owner guards), and `styles.css` (responsive controls/results).
No API, backend, database, credential, advice or prompt-editor-mode changes.

## Shared Implementation Interfaces

`style-experiment.ts` exports:

```ts
interface StyleExperimentRange {
  tagIndex: number
  min: string
  max: string
  step: string
}
interface StyleExperimentWeight {
  tagIndex: number
  label: string
  weight: string
}
interface StyleExperimentCombination {
  stylePrompt: string
  weights: StyleExperimentWeight[]
}
// Plan includes source, validated dimension metadata and total: bigint.
createStyleExperimentPlan(source: string, ranges: StyleExperimentRange[]): StyleExperimentPlan
styleExperimentCombination(plan: StyleExperimentPlan, index: bigint): StyleExperimentCombination
```

The index is zero-based. Sort selected occurrences by source order, with the
last varying fastest. Use source spans, never tag text identity, and replace
right to left against the same captured source. Reuse exact decimal parse/
format and an absolute-weight setter from prompt-weights rather than floats.
Expose dimension labels/counts/min/max/step for the configuration preview.

GenerationStore exposes:

```ts
experiment: StyleExperimentRun | null
get experimentRunning(): boolean
get operationLocked(): boolean
startStyleExperiment(source: string, ranges: StyleExperimentRange[]): Promise<void>
stopStyleExperiment(): void
clearStyleExperimentResults(): void
```

Export the run/result types from store.ts. Run fields: `status` in running,
stopping, stopped, completed, failed; `total: bigint`, `completed: bigint`
(settled/archived groups), `current: bigint` (one-based active ordinal),
`seed: number | null`, `sampleCount: number` (the frozen per-group image count),
`error: string`, and `results: StyleExperimentResult[]`.
Result fields: `ordinal: bigint`, `weights: StyleExperimentWeight[]`,
`job: GenerationView`, `images: ResultImage[]`, and `imageError: string`.
Keep any additional run token, snapshot and plan private.

## Generation State and Seeds

Validate current source equality, selected spans/ranges and a supported V4+
model before starting. Deep-copy every request field, including character
children, using existing draft validation. Preserve sample_count. Preview
group count times sample_count; do not invent per-image seeds. Validate a
bounded worst-case weighted prompt length before the first paid POST, and
validate each actual outgoing request against the existing limits.

Refactor existing ordinary submission into a shared private paid-POST path.
Reserve active operation ownership from POST through terminal observation
and image settlement. Ordinary submit, history resume and another experiment
cannot interleave while an experiment owns it. Existing onSubmitted and
first-terminal onTerminal notifications retain their history-only roles.
`operationLocked` also remains true after an accepted task's GET fails until
that task is explicitly rechecked and settled. Clearing comparison results
cannot discard its pending owner context.

When the first seed is blank, submit null once; the first generation GET
provides effective_seed even while queued/running. Latch it for the entire
run. Never submit another random request if the first GET fails. Every next
request uses the exact frozen base with its style variant and latched seed.

After terminal image retrieval settles, archive that ordinal exactly once,
then advance only if its run token is still current and no Stop/error was
latched. Do not advance from onTerminal or React effects. Stop finishes the
accepted step but prevents its successor. Any POST/GET/task/image error halts
the sequence. An explicit status recheck may settle/archive the same accepted
task; it must not restart the halted batch or duplicate its archive row.
Uncertain POST retains the existing global uncertainty/acknowledgement flow;
acknowledgement never restarts a run. Logout/dispose invalidate run tokens,
clear timers and reject stale responses. Failed logout cannot resume a batch.

## Image Ownership and UI

Move the settled active images array to its archived row, then empty active
images without revocation. Each URL has one owner. Internal step cleanup
only releases active resources; explicit experiment clear, logout/reset and
AppStore.dispose release archived URLs. Public clearResult invalidates the
sequence token; deliberate internal advancement uses a separate cleanup.
No Web Storage, IndexedDB or new server image archive is introduced.

The style heading has a button opening an inline panel. Keep configuration
mounted while hidden. Select supported parsed occurrences; show original
syntax but disable selection for unsafe weight expressions. If style source
changes during configuration, clear/invalidate old selections visibly before
Start. Provide per-occurrence decimal controls, count preview, start, Stop,
progress/seed and a concise current-page lifetime note. During a run controls
refer to its snapshot even if the draft is edited.

Render a separate paged comparison gallery labeled with ordinal, all varied
weights, request seed, job status and download links. Hide the ordinary result
view for an archived experiment job to avoid falsely saying moved images
expired; show ordinary results normally for subsequent independent jobs.
Display current batch status/Stop outside the collapsible configuration too.
Keep all produced results in memory until clear; count preview, pagination
and Stop allow managing large runs without truncating requested combinations.
Starting a new experiment explicitly replaces the previous archive only after
all preflight validation succeeds; disclose this in the configuration panel.
Ordinary submissions and invalid Start attempts preserve the archive.
No full product or future result list is allocated up front.

## Compatibility and Verification

Only current frontend files and executable frontend specs change. Existing
individual history records already store weighted style strings and seeds;
experiment grouping/progress is not durable. Rollout is a fresh web-only
release, keeping the API and prior static assets unchanged.

Independent source review must trace decimal endpoints, duplicate occurrences,
max not on grid, huge product counts/lazy access, fixed/first-random seeds,
POST uncertainty, GET recovery, terminal/image races, Stop during each phase,
normal submit/resume guards, source edits, image URL movement, logout and
disposal. Run ESLint/TypeScript and an explicit-input env-free locked build.
No frontend automated/browser tests or real paid batch execution is authorized.
