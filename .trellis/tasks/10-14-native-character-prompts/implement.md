# Implementation Plan

The operator chose native independent characters after the flat-versus-native
compatibility distinction was explained. Implement the recorded behavior.

1. Finish provider research, retaining the credential-free deployed tool schema
   and public source citations. Record default centered positioning and app cap.
2. Backend implement agent owns request validation, native MCP mapping, offline
   regressions and reviewed OpenAPI snapshot. No production/private config edits.
3. Frontend implement agent owns browser types, MobX draft and target behavior,
   prompt UI/styles and structured summaries. Match the public fields in design.
4. Independent check agent reviews the full diff and fixes real defects, checks
   cross-layer round-trip/legacy behavior and runs the required checks.
5. Main session captures contracts and validation evidence, commits the scoped
   change and records session progress. Keep broader parent release gates open.

## Progress

- [x] Pinned public provider research and non-billable deployed schema evidence.
- [x] Typed backend validation, native mapping and reviewed OpenAPI additions.
- [x] Structured frontend editor, stable tag targets, summaries and reuse.
- [x] Independent full-scope source review and required static/offline checks.
- [x] Commit `93e146b`; API-first production release `20261014T085902` verified.
- [ ] Operator desktop/mobile interaction and real-provider acceptance. Keep
  this task open while the operator tests; broader parent/provider/restore
  acceptance is unchanged.

## Checks

- Backend: frozen offline dependency sync with test/lint extras, offline pytest
  with all provider keys unset, Ruff src/tests, and offline lock consistency.
  Add meaningful cases for model/length/cap validation, schema rejection before
  paid call, exact native mapping, legacy requests, owner-scoped structured
  history and backup/restore. Update OpenAPI for the additive reviewed fields.
- Frontend: npm run lint (ESLint and TypeScript), env-free clean locked build
  with NAI_WEB_BASE_PATH=/novelai/, source review of keyboard focus, stable
  character targets, preservation on panel changes/removal/reuse and reset.
- No frontend automated/browser tests or paid calls. Source review is not
  interactive acceptance or proof of real provider output.
- Run task context validation and git diff --check before the final commit.

## Follow-up Execution: Prompt Tags and Weights

1. Record numeric-weight syntax evidence and conservative parsing behavior.
2. Implement agent owns PromptEditor.tsx, prompt-weights.ts, App.tsx integration
   and styles.css; keep source strings live in GenerationStore. Run lint and
   TypeScript. Do not add/run frontend automated tests or browser automation.
3. Independent check agent reviews parser boundaries, exact 0.1 arithmetic,
   manual-only edit transitions, label/button focus, new/removed characters,
   tag insertion, history and hidden panels. Fix real local issues.
4. Main session records contracts, builds clean explicit web inputs, commits,
   publishes a web-only release and checks public page/assets/health.

- [x] Shared tag editor and conservative source-span numeric weight editing.
- [x] Independent full-scope source review and local fixes; ESLint/TypeScript.
- [x] Fresh explicit-input, sanitized-environment offline install/build for
  `/novelai/`; source map SHA-256
  `b9fd55969666fe254073733bcd1e51b026b97b32afcd715b1085cef48a65156c`.
- [x] Web-only release `20261014T093928`; public page/asset SHA-256 and health
  checks passed. API pointer and PID unchanged; previous web assets retained.
- [ ] Operator desktop/mobile/keyboard acceptance remains pending.

## Follow-up Execution: Style Experiment

The operator requested exhaustive, seed-locked selected style-tag weight
experiments after the tag editor release. Continue with
`style-experiment-design.md` and `style-experiment-implement.md`; implementation
is split between state/helper and UI owners, followed by a full-scope check.
Work commit `5e3795f` is published as web-only release `20261014T101427`;
ESLint/TypeScript, fresh env-free build, committed-input comparison and public
page/asset/health checks passed. See the follow-up verification and deployment
notes. Operator interaction and actual-provider acceptance remain pending.

## Follow-up Execution: Compact Neutral Weights (2026-10-15)

The behavior gap belongs to shared `setPromptTagWeight`, not component
rendering: an explicit neutral assignment should remove the selected outer
numeric wrapper or preserve a plain source. The implement agent owns
`prompt-weights.ts` and, if needed for neutral-only preflight length,
`style-experiment.ts`. No parser, UI mode, API, state-machine, dependency or
credential changes are needed. Parent owns requirements/spec/release records.

1. Implement the neutral writer rule and neutral-only length accounting;
   preserve exact body/source spans and all non-neutral numeric behavior.
2. Independent full-scope check of this follow-up, especially nested/grouped
   content, two-direction returns to 1, exact decimal equivalents, right-to-
   left experiment replacement and near-limit neutral-only ranges. Run
   ESLint/TypeScript; no frontend automated/browser tests or paid calls.
3. Update executable specs, build fresh explicit env-free inputs, compare
   committed source, publish web-only, verify public hashes/health, record
   release/journal. Keep operator runtime/provider acceptance open.

- [x] Neutral source writer and one-point experiment length accounting.
- [x] Independent follow-up review, ESLint/TypeScript and clean env-free
  production build; see `neutral-weight-verification.md`.
- [x] Work commit `15f88d0` matched staged inputs; web-only release
  `20261015T073652` passed public page/asset hashes and health checks.
  See `deployment-neutral-weights-2026-10-15.md`; operator acceptance remains
  open and the API pointer/PID are unchanged.

## Follow-up Execution: Sampler Choices (2026-10-15)

The gap lives in SettingsPanel's sampler control in App.tsx. Implementer owns
App.tsx only: add the verified seven-choice list and controlled dropdown with
explicit manual entry, preserving the draft string and existing styles.
See `research/sampler-options.md`. No store/default/API/provider/dependency
or configuration change is needed. Main owns specs and release records.

1. Implement the selector/manual transitions and lossless historical values;
   run ESLint/TypeScript without frontend/helper/browser automation.
2. Independent follow-up review of all source changes and SettingsPanel,
   history reuse and frozen experiment callers; fix concrete local issues.
3. Sync specs, fresh explicit env-free build, commit, web-only publish and
   public hash/health checks; keep provider/operator acceptance open.

- [x] Seven preset choices and lossless manual-entry behavior.
- [x] Independent follow-up review, ESLint/TypeScript and fresh env-free
  production build; see `sampler-options-verification.md`.
- [ ] Committed-input comparison, web-only publish and public verification.

## Deployment Considerations (Original Native Characters)

Publishing both layers requires API-first order and a verified private backup
before restarting the API, per deploy/README.md. Check for active jobs first;
an API restart drops transient in-memory images. No schema migration is added
by this feature. Credentials remain unset unless separately configured by the
operator. Keep public page/assets/health and retained rollback targets in the
release record if deployment is performed.
