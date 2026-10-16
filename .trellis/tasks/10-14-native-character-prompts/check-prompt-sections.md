# Prompt Sections and Snapshots Independent Check

Date: 2026-10-16. Status: final full affected-layer source/static quality gate
**GREEN — SOURCE FROZEN**. This report verifies implementation and prepared
helpers; production publication and operator interaction are separate gates.

## Findings (fixed)

- File: `apps/api/tests/test_prompt_sections.py`
- Issue: the new frozen-section regression covered only manual placement with
  an explicit seed, leaving the combined metadata/mode/random-seed boundary
  and metadata-only hidden-state conflicts unverified.
- Fix: cover manual/automatic × explicit/random seed; assert frozen metadata,
  placement mode and effective seed across group execution, history, restart
  and private backup, with no replay of the interrupted ordinal. Assert changed
  metadata-only enabled state and hidden text conflict even when effective
  prompts remain identical. Add a route regression proving hidden shared text
  cannot rescue an all-zero style plan or consume a seed/create paid work.

## Findings (not fixed)

None. No backend or frontend runtime defect found in the reviewed paths.
Initial helper verification omissions were corrected by the parent and the
updated helper was independently read: loopback/public snapshot `401` with
top-level unauthenticated error and no-store, plus stopped-baseline unexpired
manifest/PNG hashes checked after API start with legitimate expiry allowed.
Helpers were not executed by the checker.

## Backend review

- Exact fixed-field/strict boolean/version metadata rejects unknown keys,
  malformed types, oversized hidden source fields and mismatched effective
  text/order/axes. Complete source people are composed then filtered, preserving
  the effective person's own coordinates when earlier cards are hidden.
- Existing effective limits, nonblank native CharacterPrompt and model gates
  remain intact. Both serializers omit absent metadata. Exact fake MCP payload
  assertions cover manual, automatic and all-hidden flat paths without hidden
  text or metadata forwarding.
- Private history/settings JSON and full frozen server definitions retain
  hidden content/order/axes without rewriting old raw definitions. Existing
  v1/v2 renderer, unknown-key conflict and missing-mode-only compatibility paths
  remain unchanged; interrupted groups are not replayed.
- Snapshot CRUD uses the existing auth/Origin/no-store boundary, strict bounded
  discriminated entries, composite owner/UUID keys, deterministic safe pagination
  and transactional idempotent/conflicting creates. DELETE checks the mutation's
  row count directly. All queries include the owner, and CRUD has no generation,
  provider or seed path.
- Schema4 is additive, explicit and readiness-probed. Disposable schema3 upgrade,
  repeated migration, auth/job/run byte preservation, restart, private modes and
  online backup tests pass. OpenAPI exactly matches the intentionally additive
  snapshot and construction creates no DB/files/provider work.
- Release helpers stage matching committed sources and an env-free locked build,
  require baseline/idle/private online backup, migrate/start API before web,
  compare running OpenAPI/public asset hashes and preserve compatible new API
  after schema4 commits, even before API validation completes. No live DB restore.

## Frontend and cross-layer review

- All 11 affected web sources were reviewed after frontend SOURCE FROZEN.
  Fixed shared/character sections are the sole editable source; request helpers
  compose enabled text in the same order/raw-single-part manner as Python and
  allocate independent complete metadata, including hidden/empty source cards.
  Hidden text is excluded from effective generation and all-zero preflight.
- Exact-section positive targets use stable person IDs and enabled fixed keys.
  Focus includes PromptEditor's text/weight/manual controls; hide/removal/reuse/
  reset/import validate the target and fall back safely. Existing weight/source
  parsing and explicit manual edit behavior are reused. Full source numbering
  and coordinates remain independent of filtered provider indices.
- Reuse deep-copies present metadata and restores legacy unsplit strings into
  their enabled 其他 sections. All new text/hide/import/position edits increment
  draft revisions; entry/session/operation guards stay intact. Malformed present
  metadata is rejected at API history/run boundaries and reuse, before it can
  replace a draft. Frozen style runs copy all nested metadata and retain mode,
  seed and the existing one-POST/read-only-reconciliation semantics.
- Snapshot save freezes only selected classifications/grouping/text and one
  client UUID/content for explicit duplicate-save verification. Import displays
  selection order and source entries, requires explicit stable character-group
  destinations, filters exact per-section scope/key, defaults to append and
  preserves destination enabled state. Repeated destinations apply in displayed
  order; replace's last entry wins, including blank text.
- Import clones the current draft, resolves every target, creates grouped new
  people and validates all raw/effective lengths, positions and six-card bounds
  before committing the two section fields together. Missing/stale targets or
  over-budget proposals make zero partial draft changes. It permits incomplete
  generation settings and empty base. Other settings/coordinates/mode persist.
- Private library pages are bounded and details have a 40-entry LRU. Page/detail
  version/controller/epoch checks reject stale responses; mutation state blocks
  overlapping save/delete. Import refreshes selected immutable details before
  applying, and reset/logout-start/401/disposal abort and clear protected state.
- Portal-backed native modal dialogs avoid nested forms and implicit generation,
  trap focus, handle Escape/backdrop, restore focus with a safe drawer fallback,
  and use bounded scroll content with persistent footer actions on narrow/short
  screens. Prompt editors remain mounted. Canvas, saved image ownership, advice,
  persistent generation/Stop controls and left tool architecture stay intact.
- Executable section/API/database/native/durable/workspace/quality/deployment
  specs are synchronized by the parent. Real browser interaction and generated
  appearance remain operator acceptance, consistent with test restrictions.

## Verification

From `apps/api`:

- `uv sync --frozen --offline --extra test --extra lint`: pass.
- Credential-unset, `UV_NO_ENV_FILE=1` frozen offline full pytest: **559 passed**
  in 32.75s after the checker test additions. Two existing dependency
  deprecations from Starlette/httpx and AnyIO remain.
- `uv run --frozen --offline --extra lint ruff check src tests`: pass.
- `uv lock --check --offline`: pass.
- Python TypeCheck: not configured.
- Web `npm run lint` (ESLint and `tsc --noEmit`): pass.
- Final full frontend/cross-layer source review: pass; no web source edits by
  checker and no rebuild required by this review.
- Parent's fresh clean build inputs exactly match the frozen current web source;
  full source/test/hash report: `/tmp/nai-prompt-sections-check-report.json`.
- Web build source-map SHA-256:
  `707ef10e4b524ea2e64314b6d7ca4a757504b5b93ab0faeb8db54faff2548c57`.
- API source/tests/contract/dependency map SHA-256:
  `15cd91eb7899d79a846852171ea3ffef748b3895b29899e288ce327790dc7ca2`.
- No frontend/helper/browser automated tests, network/paid probes, credentials,
  environment-file reads, production mutations, commits or pushes performed.
