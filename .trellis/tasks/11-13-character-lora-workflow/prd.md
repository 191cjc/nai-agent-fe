# Character LoRA preparation workflow

## Goal

Provide a connected character LoRA dataset preparation workflow: create and
revise character turnaround references with GPT while preserving the source art
style, obtain editable character prompt suggestions, then launch GPT and NovelAI
dataset runs from the confirmed references.

The user approved task creation and planning on 2026-11-13. Implementation has
not been approved; this task remains in planning.

## Background and Confirmed Facts

- Requested stages: (1) GPT three-view generation with iterative corrections,
  (2) GPT prompt suggestions followed by manual editing, and (3) starting GPT
  and NovelAI character datasets together using the three views.
- Confirmed output choice: generate three independent images (front, side and
  back). The user selected this directly; do not introduce a combined-sheet or
  cropping step.
- Confirmed persistence choice: fully save each character workflow, including
  per-view revision history, selection/rollback and recovery after refresh or
  returning in another browser session.
- Existing character creation provides references, editable identity traits,
  image-based trait advice and independent GPT/Precise libraries/style pools;
  it has no connected preparation workflow
  (`apps/web/src/CharacterDataset.tsx:27`, `:260`,
  `apps/web/src/DatasetRun.tsx:197`).
- The current GPT dataset prompt prohibits turnaround sheets and panels, so
  preparation/corrections need a distinct request purpose
  (`apps/api/src/novelai_api/gpt_images.py:37`).
- GPT receives all selected references. NovelAI Precise receives one reference
  per item in rotation and supports V4.5 only
  (`apps/api/src/novelai_api/dataset_plan.py:108`,
  `apps/web/src/store.ts:73`).
- Durable runs already freeze inputs and reference digests; GPT and NovelAI
  execute through independent lanes
  (`apps/api/src/novelai_api/style_experiments.py:262`, `:783`).

## Requirements

- R1 — Connect all three stages, carrying confirmed outputs forward without
  repeated manual reference selection.
- R2 — Generate front, side and back character views with GPT from source
  reference(s), preserving character design and original art style. Each view
  is its own image and can be generated or corrected independently.
- R3 — Support explicit correction instructions for a chosen view and selection
  of the preparation result used by subsequent stages. Select one confirmed
  image for each view. Fully save the character workflow and every view's
  revision history; allow selecting a previous result without deleting newer
  results, and restore the workflow after refresh/reentry.
- R4 — Obtain identity-focused prompt suggestions from confirmed references and
  allow manual editing before generation. Keep identity separate from per-item
  poses, scenes and styles.
- R5 — Offer one launch action for GPT and NovelAI character dataset runs based
  on the confirmed references and edited traits, with separate branch progress.
  Retain the existing independently editable provider controls and content
  libraries. Both branches must be ready before this paired launch is accepted;
  queue creation and retry reconciliation must not duplicate either branch.
- R6 — Retain dataset review, discard, caption edits, reruns and export; preserve
  frozen historical inputs and existing standalone character creation.

## Constraints

- Follow owner-private authenticated API/image boundaries; image bytes stay
  outside SQLite.
- Inspect and verify with source, schema and synthetic fixtures only. Never
  inspect real database values, reference/generated images, captions, exports or
  runtime provider payloads.
- This planning request does not authorize real paid calls, deployment or
  migration of an application database.
- Preserve unrelated uncommitted recipe-editor/spec changes in the shared tree.

## Acceptance Criteria

- [ ] AC1 / R1: Confirmed reference results and edited traits carry through the
  three stages without re-uploading or manually copying IDs.
- [ ] AC2 / R2: Preparation requests specify front/side/back views, preserve
  source design/style and yield three separately addressable single-view images,
  with no combined-sheet or cropping requirement.
- [ ] AC3 / R3: Correcting one view produces a selectable revision of that view
  without replacing the other two confirmed images; suggestions and datasets
  use the confirmed front/side/back selection. Refreshing or returning later
  restores the character workflow, revision history and selected versions;
  choosing an earlier version preserves the newer history.
- [ ] AC4 / R4: Suggested traits remain editable and are not silently applied
  or submitted to paid dataset generation.
- [ ] AC5 / R5: One launch links a GPT run and a NovelAI run to the same
  confirmed reference and trait revisions; each branch has observable progress.
  Unavailable/invalid branches block paired acceptance, and retrying a launch
  after a lost response never duplicates accepted work.
- [ ] AC6 / R6: Existing standalone creation, history, review and export remain
  compatible with historical data.
- [ ] AC7: Verification uses disposable synthetic data and fake providers,
  without private-content inspection or paid probes.

## Open Product Decisions

- Q3 — Stage one preserves the source art style. For stage three, should the
  datasets use the existing independently editable GPT/NovelAI style pools,
  or should they also preserve the original style? This is the next highest-value
  question because it changes what visual characteristics the resulting LoRA
  is encouraged to learn.

## Scope Boundary and Planning Status

- Scope covers dataset preparation, generation and existing export paths.
  GPU LoRA training, external trainer uploads and deployment are not requested.
- Source research: `research/capability-map.md`.
- Finalize `design.md`, `implement.md` and dispatch context manifests after
  blocking product decisions are resolved; do not start implementation yet.
