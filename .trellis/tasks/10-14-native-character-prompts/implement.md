# Implementation Plan

## Follow-up Execution: Per-section Assistant (2026-10-16)

1. Native frontend implementer follows section-assistant-design.md and owns
   apps/web changes only: reusable popover, independent tool requests and exact
   atomic target application; lint/TypeScript and source freeze.
2. Independent native checker reviews the full changed frontend, owning local
   fixes and npm run lint; no frontend/helper/browser tests or paid probes.
3. Parent syncs executable specs, builds fresh env-free locked sources, commits
   scoped work and publishes web-only with unchanged API pointer/PID and old
   asset/hash/health checks. Never restart API for this change.
4. Record evidence/journal; retain broader operator acceptance as in_progress.

- [x] Seven-file frontend implementation and independent full affected review
  GREEN. ESLint/TypeScript, whitespace/context validation and clean23-input
  env-free build pass; no checker source correction/rebuild. See
  check-section-assistant.md and section-assistant-build-verification.md.
- [x] Executable spec sync, final23-input build and scoped commit a2fb618;
  web-only release20261016T071424 verified with exact committed/working/build
  file-set/hashes, public HTML/JS/CSS, health and retained previous assets.
  API release20261016T064813/PID3446533 unchanged. See
  deployment-section-assistant-2026-10-16.md.
- [ ] Operator interaction/visual and actual AI/search result acceptance.

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
- [x] Work commit `8994c3d` matched staged inputs; web-only release
  `20261015T075433` passed public page/asset hashes and health checks.
  See `deployment-sampler-options-2026-10-15.md`. API pointer/PID unchanged;
  interactive/provider acceptance remains pending.

## Follow-up Execution: Definite Submission Refusal (2026-10-15)

The behavior gap spans the backend refusal boundary and GenerationStore's
sole paid submission catch. The initial frontend implementer owns store.ts.
Independent review confirmed app.py catches every RuntimeError, including
executor submission failures after history creation. A backend follow-up
implementer owns generations.py, app.py and tests/test_generations.py: add a
dedicated exception only at the initial missing-executor guard and narrow the
route catch. Generic RuntimeErrors must remain generic unknown 5xx. Do not
change queue algorithms, retries, provider error mappings or dependencies.
Parent owns artifacts/specs/staging. See `research/submission-rejection.md`.

1. Implement the narrow classification and specific not-configured message;
   run ESLint/TypeScript, no frontend/helper/browser/paid tests.
2. Independent review all follow-up source changes and normal/experiment,
   uncertainty/acknowledgement and stale/logout paths. No paid requests.
3. Run full offline backend suite, Ruff and frozen/lock consistency, plus
   regressions for true missing executor and RuntimeErrors before/after history
   creation. Recheck both layers independently, including rollout ordering.
4. Sync specs, clean env-free web build, commit and prepare matching immutable
   API/web release inputs. Do not publish this web against the old broad catch.
   Combined production switch/configuration/restart requires authorization;
   prepare the concrete enablement/rollback plan first.

- [x] Narrow frontend classification and backend dedicated exception, with
  four offline boundary regressions; no automatic retries.
- [x] Full-scope independent check passed: 215 backend tests, Ruff,
  frozen/lock consistency, frontend ESLint/TypeScript and clean build.
  See `check-submission-refusal.md`,
  `backend-submission-refusal-verification.md` and
  `submission-refusal-build-verification.md`.
- [x] After explicit authorization, activated matched release `20261015T082138`,
  configured the NovelAI provider and restarted the API. Non-billable MCP
  discovery, loaded configuration, private backups/permissions, public hashes
  and health passed. See `deployment-submission-refusal-2026-10-15.md`.
  Real paid output remains an explicit operator action; broader acceptance
  remains pending.

## Follow-up Execution: Experiment Image Navigation (2026-10-15)

The behavior gap is the paginated multi-group gallery in
StyleExperimentResults. The implementer owns only StyleExperiment.tsx and
its scoped styles.css rules: replace it with one stable image/empty-group
viewer, side arrows and scoped keyboard navigation. Keep metadata/downloads
bound to the selected row/image, traverse group order then image order,
preserve selection on append and reset it for a new/cleared experiment.
No store, API, scheduler, draft, URL ownership or ordinary-results changes.
The parent owns artifacts, specs, clean staging, commit and web publication.

1. Implement the viewer and responsive styles; run ESLint/TypeScript.
2. Independent check reviews all changed source plus store lifecycle paths,
   first/last boundaries, one/multiple images, failed/empty groups, metadata,
   downloads, keyboard scope, append stability and reset/logout behavior.
3. Sync the viewer contract and create a fresh env-free production build;
   confirm its source hashes match reviewed files and the work commit.
4. Publish only the web under existing authorization. Verify public HTML and
   asset hashes, health, retained assets and unchanged API pointer/PID.

No frontend/helper automated tests, browser automation, paid calls or
credential changes are permitted. Interactive acceptance remains with the
operator; the overall task stays active.

- [x] Implementation and independent source/static review. ESLint/TypeScript
  passed without source fixes; see `check-experiment-viewer.md`.
  Fresh env-free build and all 14 source-input hashes passed; see
  `experiment-viewer-build-verification.md`.
- [x] Fresh env-free build, source/commit match and web-only publication.
  Release `20261015T092041` passed public page/assets/health checks; API
  pointer and PID remained unchanged. See
  `deployment-experiment-viewer-2026-10-15.md`. Interactive acceptance pending.

## Follow-up Execution: Latest History on Entry (2026-10-15)

Implementer owns store.ts and App.tsx: add one-time guarded entry restore,
reuse the existing history-to-draft mapping, and keep request ownership in
stores. The parent owns artifacts/specs/build/commit/web-only deployment.
No changes to API/schema, auth protocol, generation scheduling, archive/URL
ownership, styling, dependencies or browser persistence are required.

1. Inspect initial history loading and auth/logout/reset/dispose transitions;
   implement newest-item initialization with stale/edit/operation guards.
2. Run ESLint/TypeScript. Independently source-review cookie restore/login,
   empty/failed history, legacy/structured fields and effective seed,
   superseded loads, edits/manual reuse, ordinary refresh/pagination,
   generation start, failed/successful logout, session expiry and disposal.
3. Update the workspace contract, fresh env-free build, compare reviewed
   source/commit inputs, commit and publish web-only under existing authority.
4. Verify public page/asset hashes, readiness, neighboring health, retained
   assets and unchanged API pointer/PID; record release/journal.

No frontend/helper tests, browser automation or paid calls. Broader task
remains active for operator acceptance.

- [x] Implementation and independent source/static checks. Review found no
  defects; ESLint/TypeScript and diff/context checks passed. See
  `check-history-and-drawers.md`. Combined fresh env-free build and all
  14 source-input hashes passed; see `history-and-drawers-build-verification.md`.
- [x] Fresh build, matching source commit and verified web-only publication.
  Combined release `20261015T093934` passed public page/asset hashes, health
  and retained-asset checks; API pointer/PID unchanged. See
  `deployment-history-and-drawers-2026-10-15.md`. Operator acceptance pending.

## Follow-up Execution: Left Tool Drawers (2026-10-15)

Sidebar implementer owns App.tsx and styles.css after the history implementer
froze its one-line entry initialization effect. History implementer retains
store.ts. Preserve each other's changes; parent owns all documentation/specs
and shared release work. New scope is presentation and local panel state only.

1. Replace bottom tool drawer with mutually exclusive left drawers matching
   settings. Controls: settings, history, tags, advice. Preserve mounted
   settings/tools and use disclosure button semantics and correct focus.
2. Adapt panel content to the narrow column/mobile overlay, remove dead
   bottom-drawer rules/imports and keep center results full-height.
3. Independently check both follow-ups together: panel state/focus/mobile
   sizing, no requests or resets on switching, explicit tool actions and
   uncertain-history route, initial restore/race guards and image behavior.
4. Run ESLint/TypeScript and fresh env-free build; sync specs, commit and
   publish both changes together as a verified web-only release.

No frontend/helper tests, browser automation or paid calls.

- [x] Drawer implementation and combined independent source/static checks.
  No source fixes were needed; the history initialization call, mounted tool
  state, narrow layouts and disclosure/focus behavior passed source review.
  See `check-history-and-drawers.md` and the combined build evidence.
- [x] Matching production build and verified web-only publication. Combined
  release `20261015T093934`; see `deployment-history-and-drawers-2026-10-15.md`.

## Follow-up Execution: Draggable Character Positions (2026-10-15)

Use character-position-design.md as the shared cross-layer interface. Backend
implementer owns models/adapter/offline regressions/OpenAPI; frontend implementer
owns browser types/store/position component/App/CSS. They preserve each other's
work. Parent owns docs/specs, clean staging, integration and release.

1. Implement additive bounded/defaulted coordinates and exact provider mapping;
   add meaningful offline defaults/bounds/persistence/adapter regressions.
2. Implement pointer/touch/keyboard marker control, overlap selection, reset,
   stable identities and all reuse/snapshot/draft revision paths. Run lint/types.
3. Independent combined review; full offline backend quality gate, reviewed
   OpenAPI, frontend static/source checks. No browser/helper/paid tests.
4. Update executable specs, clean env-free web build and matching immutable API
   release. Commit scoped work, take verified private online backup and inspect
   active jobs. Publish API-first, readiness then web under existing authority.
5. Verify public page/assets/schema/readiness/neighboring health, loaded release,
   retained assets and configuration continuity without exposing secrets.
   Record release/journal; broader operator/provider acceptance remains open.

- [x] Implementation and independent combined quality gate: 249 offline
  backend tests, Ruff, frozen/lock checks and web ESLint/TypeScript pass.
  See `check-character-positions.md`. Fresh env-free build and all 15 inputs
  match reviewed source; see `character-positions-build-verification.md`.
- [x] Matching source/build inputs, verified private online backup and
  API-first publication `20261015T101355`; running OpenAPI/readiness, public
  HTML/assets, retained assets, neighboring health and configuration continuity
  passed. See `deployment-character-positions-2026-10-15.md`.
- [ ] Operator desktop/mobile drag, keyboard and real-provider placement
  acceptance; broader task remains in progress.

## Deployment Considerations (Original Native Characters)

Publishing both layers requires API-first order and a verified private backup
before restarting the API, per deploy/README.md. Check for active jobs first;
an API restart drops transient in-memory images. No schema migration is added
by this feature. Credentials remain unset unless separately configured by the
operator. Keep public page/assets/health and retained rollback targets in the
release record if deployment is performed.

## Follow-up Execution: Private Seven-Day Images (2026-10-15)

Operator selected private seven-day server storage. Shared interface and
boundary: image-retention-design.md. API implementer owns all API source,
meaningful offline regressions and OpenAPI; web implementer owns browser
API/types/stores/views/styles. Parent owns artifacts/specs/check/build/release.

1. Implement private bounded persistent results, pre-paid capacity reservations,
   expiry/periodic cleanup/deletion and owner-safe reuse of existing image URLs.
2. Add validated workspace-only experiment metadata and paginated saved-group
   APIs using existing settings_json; no SQLite migration. Preserve paid queue,
   provider contract, distinct refusal and all history/native fields.
3. Add frozen run metadata, ordinary historical-image viewing and independent
   lazy saved-experiment list/viewer with session/race guards. No paid resume.
4. Independent full-scope review and meaningful full offline backend quality
   gate plus frontend lint/types/source review; no browser/helper automation.
5. Sync contracts, build fresh env-free paired releases, commit, verified private
   online backup, zero active jobs and API-first publication. Verify private
   store modes/loaded schema/public hashes/health/configuration continuity;
   record release/journal, retaining operator interaction acceptance.

- [x] Implementation and independent combined quality gate: 356 offline backend
  tests, Ruff/frozen/lock/OpenAPI, frontend lint/types/source checks all pass.
  See check-retention-and-background.md. Retention and durable scheduling
  publish together; current web build matches all 19 source/config/lock inputs.
- [x] Fresh build, commit 326d8f9 and verified paired API-first publication
  20261015T140424 with private backup, schema3 migration, exact public hashes
  and unchanged configuration. See deployment-retention-and-background-2026-10-15.md.

## Follow-up Execution: Background Style Experiments (2026-10-15)

This expands the unshipped retention follow-up. durable-experiment-design.md
owns the frozen shared API and supersedes earlier browser scheduling limits.

1. API implementer extends retained-image work with migration3, compact exact
   plans, durable run lifecycle/admission/recovery/Stop and fake regressions.
2. Web implementer replaces the paid loop with creation/observation/reattachment
   and explicit Stop, preserving draft, uncertainty and lazy saved comparison.
3. Independently check the complete combined retention+scheduler change across
   API/web/DB, full offline backend gate and frontend source/static checks.
4. Sync specifications, fresh env-free build, matched scoped commit/staging,
   reviewed backup+migration3+API-first release; verify schema/private storage,
   exact public hashes/health and unchanged provider configuration.
5. Record actual evidence and journal. Real paid/interactive acceptance remains
   with the operator; broader task stays in progress.

- [x] Combined implementation and independent full-scope quality gate, with
  corrected cleanup ownership, scheduler fairness and prompt-trim bounds.
  See check-retention-and-background.md and
  retention-and-background-build-verification.md. No paid/browser calls.
- [x] Build, private backup, schema2->3 migration and verified paired production
  publication 20261015T140424. See deployment-retention-and-background-2026-10-15.md.
- [ ] Operator real-provider/background execution and desktop/mobile interaction
  acceptance; broader task remains in progress.

## Follow-up Execution: Viewer Memory Cache (2026-10-15)

1. Implementer extends SavedResultsStore with viewer-owned path-keyed LRU,
   32-image/64 MiB limits, expiry and precise URL lifecycle; no API changes.
2. Independent static full affected-layer check and ESLint/TypeScript; no
   frontend/helper/browser automated tests or paid calls.
3. Sync specs, fresh env-free build, scoped commit and web-only publication;
   verify public hashes/health/retained assets and unchanged API pointer/PID.
4. Record evidence/journal; retain broader operator acceptance status.

- [x] Implementation and independent full affected frontend quality gate.
  See check-viewer-cache.md; fresh 19-input env-free build also passed, as
  recorded in viewer-cache-build-verification.md.
- [x] Fresh build, commit b30250c and verified web-only release 20261015T145554;
  exact public hashes/health/retained old assets pass, API pointer/PID unchanged.
  See deployment-viewer-cache-2026-10-15.md. Operator interaction remains open.

## Follow-up Execution: Canvas Layout (2026-10-16)

1. Implementer owns App.tsx/styles.css and necessary SavedResults/StyleExperiment
   visual integration only; follow canvas-layout-design.md. Keep all stores,
   API/cache/generation operations intact. Run lint/types and freeze.
2. Independent full affected frontend source/static check, including image
   selection, drawer mount/focus/form guards and persistent operation controls;
   review web build/release scripts. No frontend/helper/browser tests or paid
   probes; no unchanged-backend test repeat.
3. Parent syncs layout contracts, fresh explicit env-free locked web build,
   scoped commits and web-only release; exact public assets/health/old resources
   and unchanged live API pointer/PID, then evidence/journal.

- [x] Layout implementation and independent full affected frontend gate GREEN.
  Fixed saved-close side effects and image-height starvation; see
  check-canvas-layout.md. Final fresh 19-input build passed; see
  canvas-layout-build-verification.md.
- [x] Final fresh 19-input build, commit8f86e5a and web-only release20261016T025802.
  Exact public HTML/JS/CSS, health and retained assets verified; API pointer/PID
  unchanged. See deployment-canvas-layout-2026-10-16.md.
- [ ] Operator visual/desktop/mobile acceptance; broader task stays in_progress.


## Follow-up Execution: Experiment Zero Weight (2026-10-16)

1. Implement the scoped zero-weight-design.md cross-layer renderer/preflight
   and offline regression contract using native trellis-implement.
2. Independently review full changed behavior, static web checks and full
   offline backend gate with trellis-check, then synchronize specs.
3. Fresh env-free build and matched staging, scoped commit and API-first
   release only after no-active-work/private-backup/config-preservation gates.
4. Record deployment and journal; broader operator acceptance stays open.

- [x] Scoped implementation and independent final full affected-layer review:385
  offline backend tests, Ruff/frozen/lock/OpenAPI and web ESLint/TypeScript pass.
  Fresh 19-input env-free build passed with unchanged production sources; see
  check-zero-weight.md and zero-weight-build-verification.md.

- [x] Commit65560f3 and matched API-first release20261016T034213, published
  2026-10-16T04:06:17Z after the existing48-group run completed naturally.
  Private schema3 backup, config continuity, exact public hashes/health,
  retained assets and auth/no-store checks pass; see
  deployment-zero-weight-2026-10-16.md.
- [ ] Operator real-provider zero-omission/interaction acceptance; broader task
  remains in_progress.


## Follow-up Execution: Automatic Position (2026-10-16)

1. Native implementer follows auto-character-position-design.md for typed
   mode/UI/MCP/history/run compatibility and fake-only regressions.
2. Independent full affected-layer review and full offline backend/static web
   quality gate, then executable spec sync.
3. Fresh env-free build and scoped commits, then matched staging and API-first
   publication following the operator's subsequent restart authorization.
   Verify private online backup, idle state, running OpenAPI, public hashes,
   health, retained assets and unchanged provider configuration. No paid probe.
4. Record release evidence and progress; real-provider appearance and operator
   interaction remain acceptance checks.

- [x] Implementation and independent full affected-layer quality gate GREEN:
  462 offline backend tests, frozen sync/lock, Ruff, additive OpenAPI snapshot,
  web ESLint/TypeScript and source review. The checker corrected the character
  hint for automatic/manual mode; final source is frozen. See
  check-auto-character-position.md.
- [x] Fresh final 19-input build, source commit7c7e3d7 and matched API-first
  release20261016T060747 on2026-10-16T06:08:18Z. Private backup/idle checks,
  schema3 record continuity, exact running OpenAPI/public hashes, configuration
  continuity, retained assets and health/auth/no-store passed. See
  deployment-auto-character-position-2026-10-16.md.
- [ ] Operator real-provider placement and desktop/mobile interaction checks.

## Follow-up Execution: Prompt Sections and Snapshots (2026-10-16)

1. Backend and frontend native implementers own their package sources and follow
   the exact prompt-sections-design.md cross-layer contract; research source
   evidence is in research/prompt-sections-and-snapshots.md. No nested agents.
2. Independent final full affected-layer checker, all offline backend checks,
   web ESLint/TypeScript and exact OpenAPI; then parent executable spec sync.
3. Fresh clean build, scoped commit and matched API-first schema4 release after
   idle/private-online-backup gates; retain compatible API after migration.
4. Record deployment/journal; operator interaction/appearance remain acceptance.

- [x] Backend implementation frozen: strict metadata, private snapshot routes,
  schema4 and reviewed additive OpenAPI. Implementer full offline555 tests plus
  final snapshot/API41 checks, Ruff/frozen sync/lock passed. Final independent
  review added meaningful frozen-run coverage and passed559 tests below.
- [x] Frontend sections/library/import UI source frozen; implementer ESLint/
  TypeScript and scoped whitespace checks pass. Default append and explicit
  replace, source-person mapping and atomic incomplete-draft imports are in.
  Fresh22-input build and final independent source review pass.
- [x] Independent full affected-layer gate GREEN:559 offline backend tests,
  frozen sync/lock, Ruff, exact additive OpenAPI, frontend ESLint/TypeScript
  and source review. No web corrections; clean22-input build remains current.
  Executable sections/snapshots and deployment contracts synchronized.
- [x] Fresh22-input build, source commit9f445e5 and matched API-first release
  20261016T064813 at2026-10-16T06:48:40Z. Idle checks, verified private schema3
  online backup, schema4 preserved records, exact OpenAPI/public asset hashes,
  config continuity and loopback/public401/no-store pass. All72 unexpired
  manifest/PNG sets retain exact bytes/expiry. See
  deployment-prompt-sections-2026-10-16.md.
- [ ] Operator real interaction and resulting image appearance checks.

## Follow-up Execution: Image-service Balance (2026-10-16)

1. Backend/frontend implementers own disjoint package sources; follow frozen
   account-balance-design.md and research/account-balance.md. No paid probes.
2. Independent full affected-layer check: fake-only full backend/frozen/lock/
   Ruff/OpenAPI plus web lint/types/source lifecycle review. Sync specs.
3. Fresh env-free matched build, scoped commit, schema4 API-first release with
   idle/private-backup/config/image-preservation gates. No paid verification.
4. Record release/journal; broader operator acceptance stays open.

- [x] Balance implementation and independent full affected-layer gate GREEN:
  639 fake-only offline backend tests, frozen sync/lock, Ruff, exact additive
  OpenAPI and frontend ESLint/TypeScript/source review. No product corrections;
  paid image transport unchanged. Fresh25-input env-free web build passed.
  See check-account-balance.md and account-balance-build-verification.md.
- [x] Source commit377a634, matched API-first schema4 release20261016T090442
  and read-only configured-adapter query verified at17:05 China time. Private
  backup/idle/config/record/image gates, exact public hashes and401/no-store
  pass. All72 images retain original bytes/expiry. No paid probe. See
  deployment-account-balance-2026-10-16.md.
- [ ] Operator header interaction acceptance; broader task remains in_progress.

## Follow-up Execution: NovelAI-aware Advice (2026-10-16)

1. Native implementer owns codex_advice.py INSTRUCTIONS, SectionAssistant.tsx
   section seed and App.tsx unified advice explanation, following
   novelai-advice-design.md. No literal-copy tests or paid probes.
2. Independent full affected-layer review, full offline backend/frozen/lock/
   Ruff/unchanged OpenAPI and web lint/types/source scope review; sync specs.
3. Fresh env-free exact-input build, scoped commit, matched API-first schema4
   publication after private-backup/idle/config/image preservation gates.
4. Record release/journal; real model suggestion quality is operator acceptance.

- [x] Three-file product change and independent full affected-layer review
  GREEN:639 offline fake backend tests, frozen sync/lock, Ruff, unchanged
  OpenAPI and web ESLint/TypeScript/source review. No fixes or new literal-copy
  tests; all11 typed section scopes covered. Fresh25-input env-free build passes.
  See check-novelai-advice.md and novelai-advice-build-verification.md.
- [x] Commit14ff663 and matched API-first release20261016T094354 published
  at17:44 China time. Backup/idle/schema4/config/image continuity, exact public
  hashes/readiness/401-no-store and retained old assets passed. All72 images
  preserve original bytes/expiry. No paid AI/advice/image/provider probe. See
  deployment-novelai-advice-2026-10-16.md.
- [ ] Operator suggestion-quality acceptance; broader task remains in_progress.

## Follow-up Execution: Individual Hidden Tags (2026-10-16)

1. Backend/frontend native implementers own disjoint packages and implement
   hidden-tags-design.md. Freeze matching parser index semantics together;
   no nested delegation, no paid or frontend/helper/browser tests.
2. Independent full affected-layer checker with fake backend tests, frozen
   sync/lock/Ruff/reviewed OpenAPI and web lint/types/source review; sync specs.
3. Fresh env-free build, scoped commit and matched API-first schema4 release
   after idle/private-backup/config/image-preservation checks.
4. Record release/journal; broader operator acceptance remains in_progress.

- [x] Hidden tags implementation and independent full affected-layer gate GREEN:
  699 offline fake backend tests (60 new), frozen sync/lock, Ruff src/tests,
  exact reviewed additive OpenAPI and frontend ESLint/TypeScript/source review.
  No product corrections; assistant append spec synchronized. Fresh25-input
  env-free build passes. See check-hidden-tags.md and
  hidden-tags-build-verification.md. No paid/live provider calls or
  frontend/helper/browser automated tests.
- [x] Source commitb643e47 and matched API-first schema4 release
  20261019T023651 published on2026-10-19 at10:37 China time. Private
  backup/idle/config/record/image gates, exact running OpenAPI/public hashes,
  health and401/no-store pass. All72 image sets retain exact bytes/expiry.
  See deployment-hidden-tags-2026-10-19.md. No paid/live provider calls.
- [ ] Operator interaction acceptance; broader task remains in_progress.

## Follow-up Execution: Experiment Image Preload (2026-10-20)

1. Native implementer owns saved-results.ts, SavedResults.tsx and necessary CSS,
   implementing preload-images-design.md; no frontend/helper/browser tests.
2. Independent full affected-frontend review and ESLint/TypeScript; sync specs.
3. Fresh explicit env-free build, scoped commit and web-only publication with
   exact source/assets and unchanged API release/PID verification.
4. Record release/journal; broader operator acceptance remains in_progress.

- [x] Three-file frontend implementation and independent full affected-frontend
  check GREEN: ESLint, TypeScript and diff --check; no product corrections.
  Pagination, fixed initial count, cache/URL budgets, progress, navigation,
  cancellation and protected cleanup reviewed. Fresh25-input env-free locked
  production build passes. See check-preload-images.md and
  preload-images-build-verification.md. No frontend/helper/browser tests or
  private/paid/provider requests; backend remains unchanged.
- [x] Source commitc61e96c published as web-only release20261020T055052 on
  2026-10-20 at13:50 China time. Exact source/assets/public health and retained
  old-asset checks pass. API release/PID207197 remain unchanged; no API restart
  or private-state mutation. See deployment-preload-images-2026-10-20.md.
- [ ] Operator interaction/performance acceptance; broader task in_progress.

## Follow-up Execution: Overlay Prompt Drawer (2026-10-20)

1. Native implementer owns App.tsx and styles.css; follow
   overlay-prompt-drawer-design.md and preserve mounted editor/form behavior.
2. Independent full affected-frontend source review and ESLint/TypeScript;
   synchronize canvas-layout spec. No frontend/helper/browser tests.
3. Fresh env-free locked build, scoped commit and web-only publication with
   exact source/assets and unchanged API release/PID verification.
4. Record release/journal; keep broader task in_progress for visual acceptance.

- [x] Two-file implementation and independent full affected-frontend check
  GREEN: ESLint, TypeScript and diff --check, no product corrections. Overlay,
  constant canvas allocation, short/narrow bounds, stacking, form/focus/history
  and independent operations reviewed. Fresh25-input isolated env-free locked
  production build passes. See check-overlay-prompt-drawer.md and
  overlay-prompt-drawer-build-verification.md. No frontend/helper/browser tests
  or provider/private-image calls; backend unchanged.
- [x] Source commit8217b40 published as web-only release20261020T073033 on
  2026-10-20 at15:30 China time. Exact source/assets/public health and retained
  old assets pass. API release/PID603374 remain unchanged; no API restart or
  private-state mutation. See deployment-overlay-prompt-drawer-2026-10-20.md.
- [ ] Operator visual interaction acceptance; broader task stays in_progress.

### Full-height Clarification (2026-10-20)

1. Native implementer owns styles.css only: expanded dock fills100% of the
   stage; body fills remaining height and scrolls, removing all small-sheet
   height limits. Preserve collapsed strip and canvas allocation.
2. Independent full affected-frontend check, ESLint/TypeScript and fresh
   env-free locked build; no frontend/helper/browser tests.
3. Scoped commit and web-only publication with exact source/asset hashes,
   retained old assets and unchanged API release/PID. Record/journal; broader
   task stays in_progress for operator acceptance.

- [x] CSS-only full-height implementation and independent full affected-frontend
  check GREEN: ESLint/TypeScript/diff --check and fresh25-input isolated locked
  env-free build. No source corrections; full canvas occlusion, flex body,
  collapsed invariance, controls/layers/form/focus/cache reviewed. See
  check-full-height-prompt-drawer.md and
  full-height-prompt-drawer-build-verification.md. No frontend/helper/browser
  tests or private/paid/provider requests; backend unchanged.
- [x] Source commit38c443b published as web-only release20261020T082808 on
  2026-10-20 at16:28 China time. Exact source/assets/public health and retained
  old assets pass. API release/PID603374 remain unchanged; no restart or
  private-state mutation. See deployment-full-height-prompt-drawer-2026-10-20.md.
- [ ] Operator full-height visual acceptance; broader task stays in_progress.

## Follow-up Execution: Per-section AI Translation (2026-10-20)

1. Native frontend implementer owns SectionAssistant.tsx/styles.css; backend
   implementer owns codex_advice.py INSTRUCTIONS only. Follow
   section-translation-design.md, no nested delegation or live/paid probes.
2. Independent full affected-layer review; fake backend suite/frozen/lock/Ruff/
   unchanged OpenAPI and frontend ESLint/TypeScript/source gate. Sync specs.
3. Fresh env-free locked build and scoped commit; matched API-first schema4
   publication after private backup/idle/config/row/image-preservation gates.
4. Record release/journal; broader task stays in_progress for operator acceptance.

- [x] Frontend and INSTRUCTIONS-only backend implementation passed independent
  full affected-layer review: 699 existing offline fake backend tests, frozen
  sync/lock, Ruff src/tests, unchanged exact OpenAPI and web ESLint/TypeScript.
  No product fixes. Publication helper recovery was corrected to preserve the
  API process after startup attempt; deployment spec synchronized. Fresh
  25-input env-free locked build passed. See check-section-translation.md and
  section-translation-build-verification.md. No frontend/helper/browser tests
  or real AI/provider/paid calls.
- [x] Source commit 0b5c002 published as matched API-first release
  20261020T091846 on 2026-10-20 at17:19 China time. Private backup, idle,
  configuration/record/schema4/OpenAPI and public hash/health gates passed.
  All74 retained results/PNGs preserve exact bytes and original expiry.
  API restarted as PID657285. See deployment-section-translation-2026-10-20.md.
  No real AI/provider/paid calls or token issuance.
- [ ] Operator translation/interaction acceptance; broader task in_progress.

## Follow-up Execution: AI Configuration Reuse (2026-10-20)

1. Native implementation of optional base/model settings, bounded validation,
   configured runner wiring, fake regressions and private rotation docs.
2. Independent full backend gate, exact unchanged OpenAPI and source review
   of API-only staging/configuration activation helpers; no paid calls.
3. Scoped commit and idle/private-backup/configuration/image-preserving API
   publication. Document actual enablement and key path; record journal.
4. Keep broader task in_progress for actual advice/translation acceptance.

- [x] Optional validated base/model settings, SDK/thread wiring, meaningful
  fake regressions and private rotation docs implemented. Independent full
  backend gate: 748 fake tests, frozen sync/offline lock, Ruff src/tests and
  exact unchanged OpenAPI passed. No product corrections. Frontend unchanged;
  no frontend/helper/browser tests or actual provider/model calls.
- [x] Source commit d55b939 published as API-only release20261020T095317
  on2026-10-20 at17:54 China time. Private one-time AiQQ key/base/model copy,
  config/online SQLite backup, idle/schema4/record/image/public checks passed.
  New PID669990; all74 result/PNG bytes and expiry, web and AiQQ preserved.
  Runner wiring verified without a model turn. See deployment-advice-config-2026-10-20.md.
- [ ] Operator actual advice/translation acceptance; task remains in_progress.
