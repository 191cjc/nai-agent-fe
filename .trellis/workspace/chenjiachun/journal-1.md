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
