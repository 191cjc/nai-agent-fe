# Journal - chenjiachun (Part 1)

> AI development session journal
> Started: 2026-09-22

---



## Session 1: API quality fixes and provider readiness
<!-- trellis-session: v=2 fp=0699994de67fd57f -->

**Date**: 2026-10-08
**Task**: API quality fixes and provider readiness
**Branch**: `chore/novelai-api-quality`

### Summary

Committed bounded provider response handling and API quality fixes; recorded offline acceptance and non-billable provider readiness. Task remains open for integration and explicitly approved billable verification.

### Main Changes

- Shared MCP/tag response reader bounds decompression allocation and checks cooperative deadlines; preserves provider errors and no automatic retry of uncertain paid calls.
- Added 36 offline regressions and fixed 22 Ruff findings without changing OpenAPI; refreshed backend contracts and stale task guidance.
- Free checks passed for public health, MCP initialization/tool schema and pinned local/production Codex CLI. Production provider credentials remain unset; no paid calls or deployment performed.

### Git Commits

| Hash | Message |
|------|---------|
| `342c4cf` | fix(api): bound provider responses and pass quality checks |
| `f84ad52` | docs: record API verification and refresh task guidance |

### Testing

- [OK] 155 offline API tests passed with two dependency deprecation warnings; Ruff 0.16.8, frozen offline dependency sync, lock consistency, context manifests and diff checks passed.
- [OK] OpenAPI exact snapshot unchanged. No Python type checker configured. No frontend/browser automation performed.

### Status

[OK] **Completed**

### Next Steps

- Obtain explicit operator authorization for the exact one-image and one-advice probes documented in API verification.md; use local private credentials, no automatic retry and no production enablement.
- Integrate the reviewed branch, obtain desktop/mobile manual acceptance, verify upstream size/cost choices, and configure encrypted off-host backups with a two-account restore rehearsal before final task closure.


## Session 2: Web interaction polish
<!-- trellis-session: v=2 fp=db34827b7adcdc2f -->

**Date**: 2026-10-14
**Task**: Web interaction polish
**Branch**: `fix/web-interaction-polish`

### Summary

Aligned tool-tab keyboard navigation and synchronized parameter history on first terminal generation observation; committed the approved batch and archived the follow-up.

### Main Changes

- Shared TOOL_TABS controls rendering, keyboard order, focus and selection.
- Terminal observations notify history once before image handling; coalesced refresh follows the latest requested page and clears on reset.
- Updated the frontend workspace contract, recorded static acceptance and independent review, and archived only the scoped web follow-up.

### Git Commits

| Hash | Message |
|------|---------|
| `0501744` | fix(web): align tool navigation and refresh completed history |

### Testing

- [OK] PASS: implementation npm run lint (ESLint and TypeScript), exit 0; independent full-scope source review found no remaining issues.
- [OK] PASS: env-free locked offline npm install and /novelai/ production build; staged inputs match the reviewed source.
- [OK] PASS: Trellis context validation and git diff checks. Frontend automated/browser tests were not run under the retained operator restriction; no provider calls.

### Status

[OK] **Completed**

### Next Steps

- Desktop/mobile interactive acceptance and broader provider/deployment release gates remain with the parent tasks.
- The fix/web-interaction-polish branch is committed locally; integrate it through the normal review flow when ready.


## Session 3: Web deployment for manual testing
<!-- trellis-session: v=2 fp=1bff3555e435b97c -->

**Date**: 2026-10-14
**Task**: Web deployment for manual testing
**Branch**: `fix/web-interaction-polish`

### Summary

Published reviewed web source c63d64c to production release 20261014T082041 and verified page, assets and health endpoints. Broader deployment acceptance remains open.

### Main Changes

- Activated /srv/www/novelai/releases/20261014T082041 at https://www.firesoul.cn/novelai/; retained release 20261008T025018 and existing shared assets for rollback and open tabs.
- Used env-free committed build inputs and sanitized locked offline install/build; API release and process, SQLite and Nginx configuration were unchanged.

### Git Commits

| Hash | Message |
|------|---------|
| `b33d0a4` | docs: record verified web deployment for testing |

### Testing

- [OK] PASS: public page and new JS/CSS returned HTTP 200 and exact build SHA-256; previous JS asset remains HTTP 200.
- [OK] PASS: /novelai/api/health/ready and /aiqq/health returned HTTP 200; web pointer matched the new release and API PID/release remained unchanged.
- [OK] No paid provider calls, credential changes, frontend automated tests or browser automation; production NovelAI and Codex credentials remain unset.

### Status

[OK] **Completed**

### Next Steps

- Operator can test the interface and existing parameter history at the public URL; generation and AI advice remain disabled pending credential configuration.
- Keep deployment task open for broader provider, backup/restore and manual acceptance gates.


## Session 4: Native character prompt editor and production release
<!-- trellis-session: v=2 fp=813eb6fd89c06b84 -->

**Date**: 2026-10-14
**Task**: Native character prompt editor and production release
**Branch**: `feat/native-character-prompts`

### Summary

Implemented independent native character prompts with style/shared editing and a negative side tab; deployed API first and web release 20261014T085902 at the existing public URL.

### Main Changes

- Kept style/shared/characters distinct through browser draft, typed API, saved settings JSON, history reuse and native MCP payload; added stable tag targets and a workspace cap of six characters.
- Recorded provider source/schema evidence and saved-format rollback limitations; took a verified private snapshot and retained prior releases and assets.

### Git Commits

| Hash | Message |
|------|---------|
| `93e146b` | feat: add native character prompt editor |
| `6ab708e` | docs: record native prompt editor production release |

### Testing

- [OK] PASS: 211 offline backend tests, Ruff, frozen offline dependencies and lock consistency; frontend ESLint/TypeScript and env-free clean /novelai/ production build.
- [OK] PASS: independent full-scope source review, exact deployed page/asset hashes, public API and /aiqq health, local new schema and active release pointers.
- [OK] No frontend automated/browser tests, paid provider calls or credential changes. Production remains provider-disabled; real image output and interactive acceptance are pending.

### Status

[OK] **Completed**

### Next Steps

- Operator should hard refresh https://www.firesoul.cn/novelai/ and test style/shared/character editing, add/remove controls, side tabs and tag destinations on desktop/mobile.
- Keep native prompt task and broader release tasks open for manual/provider acceptance; retain new API during frontend fallback and verify saved-format compatibility before any API downgrade.


## Session 5: Prompt tags and weight controls deployed
<!-- trellis-session: v=2 fp=021b0d7a193add90 -->

**Date**: 2026-10-14
**Task**: Prompt tags and weight controls deployed
**Branch**: `feat/native-character-prompts`

### Summary

Implemented blur-to-tag prompt editing with manual-only text mode and precise 0.1 weight controls; deployed fresh web release 20261014T093928. Keep native-character-prompts open for operator interaction acceptance.

### Main Changes

- Shared controlled editor covers style, shared, native characters and global negative; exact decimal numeric emphasis preserves source spans and complex original syntax.
- Independent review fixed blur layout movement and ambiguous trailing-colon handling; API and existing draft/history/auth lifecycle preserved.

### Git Commits

| Hash | Message |
|------|---------|
| `0d12ea3` | feat(web): add prompt tags with precise weight controls |
| `9f9dc24` | docs: record prompt weight editor production release |

### Testing

- [OK] PASS: ESLint/TypeScript, independent full-scope source review, context validation and diff checks; no frontend automated tests or browser automation.
- [OK] PASS: fresh explicit-input env-free offline locked production build; committed source and public page/assets match SHA-256; health and retained old assets passed.

### Status

[OK] **Completed**

### Next Steps

- Operator refreshes https://www.firesoul.cn/novelai/ and accepts desktop/mobile/keyboard tag, arrow and manual-edit interactions; no paid provider output was exercised.


## Session 6: Style weight experiment and web-only release
<!-- trellis-session: v=2 fp=1e1e497ef2847708 -->

**Date**: 2026-10-14
**Task**: Style weight experiment and web-only release
**Branch**: `feat/native-character-prompts`

### Summary

Implemented occurrence-based exact Cartesian style-weight experiments with frozen parameters, shared seeds, sequential image archival and paged comparisons; deployed web-only release 20261014T101427.

### Main Changes

- Added BigInt lazy range enumeration, per-tag min/max/step controls, preflight group/image totals and source-preserving absolute weight replacement.
- GenerationStore owns frozen runs, first-effective-seed reuse, Stop/error/no-retry behavior, accepted-task manual rechecks and archived URL cleanup.
- Published https://www.firesoul.cn/novelai/ from committed explicit env-free inputs; retained old releases/assets and kept API release/PID unchanged.

### Git Commits

| Hash | Message |
|------|---------|
| `5e3795f` | feat(web): add exhaustive style weight experiments |
| `dff61be` | docs: record style experiment production release |

### Testing

- [OK] Independent full-scope source review, ESLint, TypeScript, Trellis context validation and git diff --check passed.
- [OK] Fresh locked offline install and sanitized production build passed; all 14 inputs matched reviewed and committed sources.
- [OK] Public page/referenced assets passed exact SHA-256; API readiness, neighboring service and prior asset checks returned HTTP 200. No frontend tests, browser automation or paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator desktop/mobile/keyboard and real-provider experiment acceptance; retain active task in_progress pending that acceptance.


## Session 7: Compact neutral weights and web-only release
<!-- trellis-session: v=2 fp=371c9720c1028c1f -->

**Date**: 2026-10-15
**Task**: Compact neutral weights and web-only release
**Branch**: `feat/native-character-prompts`

### Summary

Exact neutral prompt weights now omit their outer numeric wrappers across all prompt controls and style experiments; published web-only release 20261015T073652.

### Main Changes

- Shared weight setter preserves exact inner text and surrounding source when returning to 1.0; neutral-only experimental ranges use compact output length.

### Git Commits

| Hash | Message |
|------|---------|
| `15f88d0` | fix(web): omit neutral prompt weight wrappers |
| `2c4f6b2` | docs: record compact neutral weights release |

### Testing

- [OK] Independent follow-up source review, ESLint/TypeScript, context validation, diff check and fresh explicit-input env-free offline production build passed.
- [OK] All 14 staged inputs matched reviewed and committed source. Public HTML and referenced assets matched SHA-256, health and prior asset checks passed; API pointer/PID unchanged.

### Status

[OK] **Completed**

### Next Steps

- Operator interaction/provider acceptance remains pending. No frontend/helper automated tests, browser automation or paid calls were run; keep broader task in_progress.


## Session 8: Sampler dropdown and web-only release
<!-- trellis-session: v=2 fp=8d148fb183b9bdd4 -->

**Date**: 2026-10-15
**Task**: Sampler dropdown and web-only release
**Branch**: `feat/native-character-prompts`

### Summary

Added seven source-backed sampler choices with lossless manual/history values; published web-only release 20261015T075433.

### Main Changes

- SettingsPanel now provides an actual sampler select with names/IDs and explicit manual entry while retaining the controlled draft and initial blank value.

### Git Commits

| Hash | Message |
|------|---------|
| `8994c3d` | feat(web): add sampler selection options |
| `e712005` | docs: record sampler selection production release |

### Testing

- [OK] Independent source review, ESLint/TypeScript, context validation, diff check and fresh explicit-input env-free offline production build passed.
- [OK] All 14 inputs matched reviewed/committed source. Public page/assets matched SHA-256; API readiness, neighboring health and prior assets passed. API pointer/PID unchanged.

### Status

[OK] **Completed**

### Next Steps

- Operator interaction/provider acceptance remains pending; no frontend/helper automated tests, browser automation or paid calls ran. Keep task in_progress.


## Session 9: Fix submission refusal and enable production images
<!-- trellis-session: v=2 fp=1dd75bbd85401b51 -->

**Date**: 2026-10-15
**Task**: Fix submission refusal and enable production images
**Branch**: `feat/native-character-prompts`

### Summary

Diagnosed repeated 503 from an unconfigured NovelAI provider, corrected backend refusal typing and frontend uncertainty handling, and activated matched API/web release 20261015T082138 after explicit operator authorization.

### Main Changes

- Dedicated GenerationNotConfigured boundary preserves unknown outcomes for generic server/transport errors and stops experiments without retries.
- Copied only existing NovelAI URL/token into private production configuration, preserved unrelated settings, backed up private state, and enabled the provider with API-first publication.

### Git Commits

| Hash | Message |
|------|---------|
| `be99b7d` | fix: distinguish unconfigured generation submissions |
| `c020ab5` | docs: record image provider activation authorization |
| `3ef513e` | docs: record production image provider activation |

### Testing

- [OK] 215 offline backend tests, Ruff, frozen dependency and lock checks; frontend ESLint/TypeScript and fresh env-free production build passed.
- [OK] Non-billable MCP discovery/native schema, loaded process configuration, public page/resource hashes, readiness, AiQQ health, backup permissions and SQLite ownership passed; no paid or browser/frontend automated tests.

### Status

[OK] **Completed**

### Next Steps

- Operator tests real image output and desktop/mobile acceptance; keep the broader task active and retain the corrected API even when rolling back web.


## Session 10: Style experiment image navigation
<!-- trellis-session: v=2 fp=26ed5f38e039684b -->

**Date**: 2026-10-15
**Task**: Style experiment image navigation
**Branch**: `feat/native-character-prompts`

### Summary

Replaced the style-experiment gallery with a single-image viewer, independently checked and published web-only release 20261015T092041.

### Main Changes

- One contained image with side arrows and scoped left/right keys; metadata/downloads and failed groups stay reachable.
- Preserve current selection on appended results; reset for new/cleared experiments. Store/API/URL ownership unchanged.

### Git Commits

| Hash | Message |
|------|---------|
| `1f9045d` | feat: add arrow navigation to style experiments |
| `545999b` | docs: record experiment viewer deployment |

### Testing

- [OK] Independent source review, ESLint/TypeScript, diff/context checks and fresh env-free production build passed; all 14 build inputs match reviewed and committed source.
- [OK] Public HTML and JS/CSS hashes, readiness, neighboring health and retained assets passed. API release/PID unchanged; no frontend/helper/browser tests or paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator verifies desktop/mobile and keyboard comparisons with actual images; broader task remains active pending acceptance.


## Session 11: Latest history restoration and left tool drawers
<!-- trellis-session: v=2 fp=98243116c4c04f14 -->

**Date**: 2026-10-15
**Task**: Latest history restoration and left tool drawers
**Branch**: `feat/native-character-prompts`

### Summary

Implemented guarded latest-history draft restoration and unified left tool drawers; independently checked and published web-only release 20261015T093934.

### Main Changes

- Restore newest history prompts/native characters/settings/effective seed once per authenticated entry; late responses cannot overwrite edits or newer operations/sessions.
- Settings/history/prompt lookup/AI advice now share left drawers with preserved mounted state, close/focus/mobile behavior; bottom drawer removed.

### Git Commits

| Hash | Message |
|------|---------|
| `5b48196` | feat: restore latest settings and move tools into sidebar |
| `0a333ba` | docs: record workspace entry and sidebar deployment |

### Testing

- [OK] Independent combined source review, ESLint/TypeScript, context/diff checks and fresh env-free production build passed; all 14 source inputs match reviewed commit.
- [OK] Public HTML and JS/CSS hashes, readiness, neighboring health and retained assets passed. API pointer/PID unchanged; no frontend/helper/browser tests or paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator interaction acceptance remains pending; user is considering intuitive per-character action/clothing controls as a design discussion, not yet implementation.


## Session 12: Draggable character positions and paired release
<!-- trellis-session: v=2 fp=0b8e0eb324f51bda -->

**Date**: 2026-10-15
**Task**: Draggable character positions and paired release
**Branch**: `feat/native-character-prompts`

### Summary

Added bounded draggable character positions across UI, API, provider and parameter history; published matched API-first release 20261015T101355.

### Main Changes

- Added stable numbered mouse/touch markers, overlap selection, keyboard micro-adjustment and center reset; preserved positions through history entry/reuse and frozen experiments.
- Added strict defaulted finite 0.1–0.9 coordinates, exact ordered MCP mapping and additive OpenAPI; synchronized executable contracts and release evidence.
- Published paired API/web release 20261015T101355 after verified private online backup and zero-active-job checks; configuration unchanged and previous assets/releases retained.

### Git Commits

| Hash | Message |
|------|---------|
| `31cff3e` | feat: add draggable character positions |
| `140bea2` | docs: record character position deployment |

### Testing

- [OK] Independent review: 249 offline backend tests, Ruff, frozen sync/lock checks, frontend ESLint/TypeScript and diff/context validation passed.
- [OK] Fresh env-free build: all 15 web/19 API inputs matched committed source; running OpenAPI, public HTML/JS/CSS hashes, readiness and neighboring health passed. No frontend/browser automation or paid provider calls.

### Status

[OK] **Completed**

### Next Steps

- Operator validates desktop/mobile drag, keyboard behavior and actual generated placement. Keep native-character task and broader acceptance gates in progress.


## Session 13: Retained images and durable background style experiments
<!-- trellis-session: v=2 fp=c5a4802df3b933aa -->

**Date**: 2026-10-15
**Task**: Retained images and durable background style experiments
**Branch**: `feat/native-character-prompts`

### Summary

Implemented private seven-day disk images with bounded admission and lazy owner-only historical comparisons; migrated schema2 to3 for server-owned exact style batches, fixed seed, failed-group continuation, explicit Stop, reattachment and no duplicate paid retry after interruption. Independent full-scope check passed: 356 offline tests, Ruff/frozen/lock/OpenAPI, frontend ESLint/TypeScript and 19-input env-free build. Published paired release20261015T140424 after verified private online backup and zero-active checks; loaded API/public asset hashes, schema/integrity, private modes, auth guards, neighboring health and configuration continuity passed. No paid/browser/frontend/helper tests or credential/env/unit/Nginx changes. Broader task remains in_progress for operator/provider acceptance; no push or archive.

### Git Commits

| Hash | Message |
|------|---------|
| `326d8f9be3a899461b31027d8a7e177902a2ed8d` | feat: retain images and run style experiments in background |
| `e150031` | docs: record retained images and background experiment deployment |

### Status

[OK] **Completed**


## Session 14: Bounded viewer image cache and web release
<!-- trellis-session: v=2 fp=f2541d324f3617ff -->

**Date**: 2026-10-15
**Task**: Bounded viewer image cache and web release
**Branch**: `feat/native-character-prompts`

### Summary

Added and published viewer-local LRU image caching so saved-image comparisons reuse PNG bytes within 32 entries and 64 MiB, with fresh authenticated metadata and original expiry.

### Main Changes

- SavedResultsStore owns cached versus transient URLs; navigation, expiry, LRU eviction and session cleanup preserve independent ordinary-generation and background-run state.
- Synchronized viewer cache specs/task context; web-only release 20261015T145554 preserves API release20261015T140424 and PID3184888.

### Git Commits

| Hash | Message |
|------|---------|
| `b30250c` | perf: cache recently viewed history images |
| `42a89f2` | docs: record viewer cache deployment |

### Testing

- [OK] Independent affected frontend source review, ESLint/TypeScript, diff/context checks and a fresh 19-input env-free locked build passed.
- [OK] Exact public HTML/JS/CSS, readiness, neighboring health and previous assets passed; no API restart, frontend/helper/browser automated tests or paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator verifies arrow comparison and outstanding real-provider/background/desktop/mobile acceptance; keep the broader task in_progress.


## Session 15: Canvas workspace and bottom prompt drawer release
<!-- trellis-session: v=2 fp=92e5a1d9d13c4130 -->

**Date**: 2026-10-16
**Task**: Canvas workspace and bottom prompt drawer release
**Branch**: `feat/native-character-prompts`

### Summary

Implemented and published a canvas-centered workspace with mounted collapsible bottom prompts, persistent Generate, local current-image arrows/thumbnails, and integrated retained-result comparison.

### Main Changes

- Kept prompt/editor/configuration state mounted and operation controls outside disclosure; history reuse/resume use explicit safe navigation and focus.
- Independent review fixed saved-close left-panel side effects and metadata starving image height; proportional canvas regions and short-screen scroll bounds recorded in specs.
- Web-only release20261016T025802 preserves live API20261015T140424 and PID3184888, credentials/schema and background experiment execution.

### Git Commits

| Hash | Message |
|------|---------|
| `8f86e5a` | feat: center workspace on image canvas with bottom prompt drawer |
| `e9d3672` | docs: record canvas layout deployment |

### Testing

- [OK] Independent full affected frontend source review, ESLint/TypeScript, diff/context validation and final 19-input explicit env-free locked build passed.
- [OK] Final committed-source/public HTML/JS/CSS hashes, readiness, neighboring health and retained assets passed; superseded preliminary builds were not published. No frontend/helper/browser automation or paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator visual, desktop/mobile and outstanding real-provider acceptance; keep broader native-character task in_progress.


## Session 16: Experiment zero weight omission and paired production release
<!-- trellis-session: v=2 fp=b58b375dd685302d -->

**Date**: 2026-10-16
**Task**: Experiment zero weight omission and paired production release
**Branch**: `feat/native-character-prompts`

### Summary

Implemented exact-zero omission for new style experiments with browser/server parity, occurrence-safe separator edits, retained comparison metadata, empty/length preflight and frozen legacy v1 run compatibility. Independent gate:385 offline backend tests, Ruff/frozen/lock/OpenAPI and frontend ESLint/TypeScript; fresh19-input env-free web build. Waited for existing48-group experiment to complete naturally with48 successes, then published matched API/web20261016T034213 at2026-10-16T04:06Z after private schema3 online backup. Exact public hashes/readiness/auth-no-store, config continuity and retained assets passed. No frontend/browser tests, paid probes, env/unit/Nginx edits or push. Broader real-provider/visual acceptance remains in_progress.

### Git Commits

| Hash | Message |
|------|---------|
| `65560f3` | fix: omit zero-weight tags from new style experiments |
| `4eb44fc` | docs: record zero-weight experiment deployment |

### Status

[OK] **Completed**


## Session 17: Automatic character positioning deployed
<!-- trellis-session: v=2 fp=ad4e0ed41073da87 -->

**Date**: 2026-10-16
**Task**: Automatic character positioning deployed
**Branch**: `feat/native-character-prompts`

### Summary

Added explicit automatic/manual character placement, preserved legacy history and frozen experiment semantics, and deployed matched API/web after later restart authorization.

### Main Changes

- Strict default-false stored mode; automatic MCP payload omits child x/y, manual retains exact coordinates, unsupported automatic capability fails before paid calls.
- Native selector releases dragging and preserves coordinates; summaries, reuse and immutable server experiments retain placement mode.
- Published release 20261016T060747 after private online backup and zero-active-work preflight; schema3, existing state/images and provider configuration preserved.

### Git Commits

| Hash | Message |
|------|---------|
| `7c7e3d7` | feat: add automatic character positioning |
| `b856e1f` | docs: record automatic positioning deployment |

### Testing

- [OK] 462 offline backend tests, frozen sync/lock, Ruff, reviewed additive OpenAPI and web ESLint/TypeScript passed; final 19-input env-free build matches committed source.
- [OK] Verified exact running OpenAPI, public HTML/JS/CSS hashes/readiness, retained assets, private image root, neighboring health and unauthenticated no-store boundaries; no paid calls or browser tests.

### Status

[OK] **Completed**

### Next Steps

- Operator validates real NovelAI placement and desktop/mobile interaction; broader native-character task remains in_progress.


## Session 18: Prompt sections and private snapshots deployed
<!-- trellis-session: v=2 fp=fbcf6705378f488b -->

**Date**: 2026-10-16
**Task**: Prompt sections and private snapshots deployed
**Branch**: `feat/native-character-prompts`

### Summary

Implemented shared scene/other and seven per-character sections, hidden effective projection with complete private metadata, named multi-section private snapshots, ordered batch imports with explicit person mapping and atomic append/default or replace. Independent full-scope review passed 559 offline backend tests, Ruff/frozen sync/lock/OpenAPI, frontend ESLint/TypeScript and a clean 22-input env-free build. Deployed matched API-first schema4 release 20261016T064813 after idle checks and a verified private online backup. Running schema/public hashes/auth-no-store/health/config continuity passed; all 72 unexpired manifest/PNG sets retained exact bytes and expiry. No paid probes or frontend/helper/browser automated tests. Broader task stays in_progress for operator visual/interaction and provider acceptance; unrelated tasks untouched.

### Git Commits

| Hash | Message |
|------|---------|
| `9f445e5` | feat: add prompt sections and private snapshots |
| `6b6c040` | docs: record prompt sections deployment |

### Status

[OK] **Completed**


## Session 19: Per-section AI and tag-search assistant deployed
<!-- trellis-session: v=2 fp=0126f5712356b885 -->

**Date**: 2026-10-16
**Task**: Per-section AI and tag-search assistant deployed
**Branch**: `feat/native-character-prompts`

### Summary

Added compact assistant popovers to shared/person/style/negative prompts with AI advice and prompt-search tabs. Current-section consultation is editable and explicitly submitted; suggestions and canonical search tags support exact stable-target append/replace, preserving hidden state and validating relevant budgets atomically before settings are complete. Independent full affected frontend review, ESLint/TypeScript, context/whitespace and final 23-input env-free locked build passed; no source correction. Strengthened publication with exact committed/working/build file-set equality. Published web-only release 20261016T071424 with exact public hashes, retained old assets and health checks. API release20261016T064813/PID3446533 unchanged; no restart, backend/runtime changes, paid probes or frontend/helper/browser automated tests. Broad task stays in_progress for interaction and AI/search content acceptance; unrelated active tasks left untouched.

### Git Commits

| Hash | Message |
|------|---------|
| `a2fb618` | feat: add section prompt assistant |
| `4ed4e80` | docs: record section assistant deployment |

### Status

[OK] **Completed**


## Session 20: Image-service Anlas balance header
<!-- trellis-session: v=2 fp=9a0e0be77f438074 -->

**Date**: 2026-10-16
**Task**: Image-service Anlas balance header
**Branch**: `feat/native-character-prompts`

### Summary

Implemented and deployed authenticated normalized NovelAI Anlas header with strict allowlist, short singleflight cache, truthful freshness and protected refresh lifecycle. Independent gate: 639 offline backend tests, Ruff/frozen/lock/OpenAPI and web ESLint/TypeScript/source review passed; fresh25-input env-free build. Matched schema4 API/web release20261016T090442 after idle/private backup checks; all72 retained image bytes/expiry and provider config preserved. Live read-only adapter probe passed, no paid calls. Header interaction remains operator acceptance; broader task stays in_progress, unrelated tasks untouched.

### Git Commits

| Hash | Message |
|------|---------|
| `377a634` | feat: show image service Anlas balance |
| `2fd539b` | docs: record Anlas balance deployment |

### Status

[OK] **Completed**


## Session 21: NovelAI-aware advice and section scopes
<!-- trellis-session: v=2 fp=d0e9d48ef1be82f0 -->

**Date**: 2026-10-16
**Task**: NovelAI-aware advice and section scopes
**Branch**: `feat/native-character-prompts`

### Summary

Strengthened fixed advice guidance for NovelAI/Danbooru-compatible English tags; visible editable scoped consultations cover all11 typed destinations and only current-section text. Unified advice UI explains purpose. Independent639 fake-only offline backend tests, frozen/lock/Ruff/unchanged OpenAPI and web ESLint/TypeScript/source checks passed; fresh25-input clean build. Matched API/web release20261016T094354 at17:44 China time after backup/idle checks; schema4, config and all72 image bytes/expiry retained. Zero paid model/provider probes. Actual suggestion quality remains operator acceptance; broader task open.

### Git Commits

| Hash | Message |
|------|---------|
| `14ff663` | feat: guide advice with NovelAI section tags |
| `6344a67` | docs: record NovelAI advice guidance deployment |

### Status

[OK] **Completed**


## Session 22: Individual hidden prompt tags and API-first release
<!-- trellis-session: v=2 fp=d26d63987733cd5e -->

**Date**: 2026-10-19
**Task**: Individual hidden prompt tags and API-first release
**Branch**: `feat/native-character-prompts`

### Summary

Implemented per-tag hide/restore using whole-line comments and guarded blur formatting; persisted raw history/snapshots while effective generation excludes hidden text. Added strict opt-in compatibility flag, safe appends and frozen experiment compatibility. Independent699 fake backend tests, Ruff/frozen lock, web lint/types and env-free build passed. Deployed matched20261019T023651 API-first after idle/private backup; schema4/config/records and all72 retained images/expiry preserved. No paid/live provider calls. Broader task remains in_progress for operator acceptance.

### Git Commits

| Hash | Message |
|------|---------|
| `b643e47` | feat: hide individual prompt tags with line comments |
| `737811e` | docs: record individual hidden tags deployment |

### Status

[OK] **Completed**


## Session 23: Experiment image preload
<!-- trellis-session: v=2 fp=bef79ab521582fcd -->

**Date**: 2026-10-20
**Task**: Experiment image preload
**Branch**: `feat/native-character-prompts`

### Summary

Added explicit saved-experiment image preloading with progress, cancellation, cached reuse, per-image failure continuation and bounded 256-image/256-MiB session memory. Independent frontend review, ESLint/TypeScript and fresh 25-input env-free locked build passed. Published web-only release 20261020T055052; exact public assets and readiness verified, old assets retained, API release/PID 207197 unchanged. No API restart, private-state mutation, frontend/helper/browser tests or provider calls. Broader task stays in_progress for operator acceptance.

### Git Commits

| Hash | Message |
|------|---------|
| `c61e96c` | feat: preload saved experiment images on demand |
| `79528ff` | docs: record experiment image preload deployment |

### Status

[OK] **Completed**


## Session 24: Overlay prompt drawer
<!-- trellis-session: v=2 fp=eddb9c4369664454 -->

**Date**: 2026-10-20
**Task**: Overlay prompt drawer
**Branch**: `feat/native-character-prompts`

### Summary

Changed the bottom prompt drawer to a bounded absolute overlay within a local canvas stage. A constant toggle strip preserves canvas/image size across disclosure; operation/recovery/Generate controls remain outside. Independent affected-frontend review, ESLint/TypeScript and fresh 25-input env-free locked build passed. Published web-only release 20261020T073033; exact public assets, retained previous assets and readiness verified; API release/PID 603374 unchanged. No API restart, private-state mutation, frontend/helper/browser tests or provider calls. Broader task remains in_progress for visual acceptance.

### Git Commits

| Hash | Message |
|------|---------|
| `8217b40` | fix: overlay prompt drawer without resizing canvas |
| `dd282e7` | docs: record overlay prompt drawer deployment |

### Status

[OK] **Completed**


## Session 25: Full-height prompt drawer
<!-- trellis-session: v=2 fp=4751b0dccaf657c1 -->

**Date**: 2026-10-20
**Task**: Full-height prompt drawer
**Branch**: `feat/native-character-prompts`

### Summary

Applied operator clarification: expanded prompt drawer fills the entire canvas stage and occludes the full image. Removed former 28dvh/300px and short-screen23dvh heights; flex body scrolls internally. Collapsed strip, canvas allocation and persistent controls unchanged. Independent affected-frontend review, ESLint/TypeScript and fresh25-input env-free locked build passed. Published web-only release20261020T082808; exact public assets/health and retained previous assets verified, API release/PID603374 unchanged. No API restart, private-state mutation, frontend/helper/browser tests or provider calls. Broader task remains in_progress for visual acceptance.

### Git Commits

| Hash | Message |
|------|---------|
| `38c443b` | fix: expand prompt drawer over the entire canvas |
| `926f6f6` | docs: record full-height prompt drawer deployment |

### Status

[OK] **Completed**


## Session 26: Per-section AI translation released
<!-- trellis-session: v=2 fp=e0664ef1829b3638 -->

**Date**: 2026-10-20
**Task**: Per-section AI translation released
**Branch**: `feat/native-character-prompts`

### Summary

Added read-only current-section Chinese AI explanations and explicit questions; independently verified and deployed matched API/web release 20261020T091846 with private backup and all 74 retained images preserved.

### Main Changes

- Section helper now provides advice, translation and tag search with independent request state, bounded current-source input, stale explanation guards and no draft application.
- Backend INSTRUCTIONS distinguish Chinese explanations from English composition tags; API/runtime/schema/dependencies remain unchanged.
- Corrected activation recovery to preserve the modern API process after startup attempt and captured the contract; API-first publication completed with PID657285.

### Git Commits

| Hash | Message |
|------|---------|
| `0b5c002` | feat: explain section prompts with AI translation |
| `4637ab6` | docs: record section translation deployment |

### Testing

- [OK] 699 existing fake-only backend tests, frozen sync, offline lock, Ruff src/tests and unchanged exact OpenAPI passed; backend has no configured type checker.
- [OK] Web ESLint/TypeScript, independent full affected-layer source review and fresh 25-input env-free locked production build passed; no frontend/helper/browser automated tests or real AI/provider/paid calls.
- [OK] Private verified online backup, zero-active-work restart gates, preserved rows/config/schema4 and all 74 retained result/PNG bytes and original expiry; exact public assets/readiness, retained old assets and unauthenticated401/no-store passed.

### Status

[OK] **Completed**

### Next Steps

- Operator acceptance of translation quality and desktop/mobile interaction; keep current and other tasks in_progress, without archiving.


## Session 27: Restore advice configuration from AiQQ
<!-- trellis-session: v=2 fp=203243810a961f93 -->

**Date**: 2026-10-20
**Task**: Restore advice configuration from AiQQ
**Branch**: `feat/native-character-prompts`

### Summary

Diagnosed missing advice key503, added optional HTTPS endpoint/model wiring, and privately copied user-authorized AiQQ text-AI configuration into independent NovelAI config; API-only release20261020T095317.

### Main Changes

- Optional validated NAI_CODEX_BASE_URL and NAI_CODEX_MODEL reach pinned SDK/thread while preserving stdin authentication, isolated environment and default behavior.
- Private one-time key/base/model copy to root0600 /etc/novelai/api.env; documented sudoedit and idle restart for future key rotation.

### Git Commits

| Hash | Message |
|------|---------|
| `d55b939` | fix: configure advice endpoint and model |
| `a9696ba` | docs: record advice configuration enablement |

### Testing

- [OK] Independent full backend gate:748 fake tests, frozen sync/offline lock, Ruff src/tests and exact unchanged OpenAPI passed; backend type checker not configured.
- [OK] Exact immutable API staging, CLI0.152.1, no-turn configured runner probes, private config/online DB backup, idle/schema4/rows/config/images/expiry preservation, unchanged web/AiQQ and public readiness passed; no real model/provider/paid calls.

### Status

[OK] **Completed**

### Next Steps

- Operator retry of advice/translation and actual model compatibility/quality acceptance; keep broader task in_progress without archiving.
