# Per-section AI Translation Independent Review (2026-10-20)

## Result

Affected-layer quality gate GREEN. No product-source correction was required;
the frozen frontend build remains current. One publication-helper failure-path
finding was corrected by the parent and source-reviewed again below. Actual
model explanation quality and browser interaction remain operator acceptance.

## Scope and source findings

- Reviewed SectionAssistant.tsx, its three translation CSS rules, the
  codex_advice.py INSTRUCTIONS-only diff, related Editor/GenerationStore/API
  lifecycle paths, latest translation design, and frontend/backend contracts.
- All existing section helpers expose AI 建议 / AI 翻译 / 提示词搜索 in that
  order. Tab activation only changes local state; the existing roving tablist,
  portal bounds, Escape/outside close, safe focus return and disclosure hiding
  remain intact. The full-height prompt drawer and canvas CSS are unchanged.
- Translation resolves exact raw text with promptTextAt(stable target), including
  weights and hidden comment lines. It shows that text read-only, freezes the
  latest source/question at explicit submit and includes only that source,
  question, section label and typed purpose in the advice input. Other section
  content, settings, images and advice history are not read for its consultation.
- Translation has an independent useLocalRequest instance, question, snapshot,
  local validation error, loading, request error and cooldown. Question edits
  cancel/invalidate the request and clear its old result. Switching tabs retains
  local state without submitting. Source changes mark the frozen snapshot stale
  and hide its explanation; the next explicit request resolves the latest source.
- Empty source/question, question>500 and consultation>4000 cannot submit.
  The translation path never slices or silently truncates the source. Returned
  suggestion must be a nonblank string<=3000. Plain React text preserves line
  breaks and wraps; there is no Markdown/HTML execution, append/replace control,
  call to applyPromptText, automatic draft edit, chat thread or persistence.
- Existing stable opening/revision/target/visible-opener guards remain in force.
  Editor unmounts invalid/disclosed/session-reset helpers; useLocalRequest aborts,
  advances its epoch, rejects late results and clears timer ownership on cleanup.
  Ctrl/Cmd+Enter is explicit and composition-aware; all buttons use type=button,
  and portal Enter handling cannot submit the enclosing generation form.
- Runtime instructions now explicitly distinguish English comma-separated
  composition tags from concise Chinese explanations of existing tags. They
  preserve original tags, uncertainty and relevant weight/comment semantics,
  including workspace-only whole-line comments and literal inline/escaped
  markers. Strict JSON, no-tool/no-image instructions, isolation, SDK/CLI pins,
  output limits, deadlines and runner implementation remain unchanged.
- POST /api/advice remains {input}->{suggestion}; API models, OpenAPI snapshot,
  dependencies/locks, database schema, image-provider and generation paths are
  unchanged. Existing fake runtime/contract tests are appropriate for this
  instruction-only backend change; no literal-copy tests were added.
- Frontend section-assistant and backend advice specs match these paths. The
  parent's deployment-spec addition also matches the resolved startup recovery
  boundary described below.

## Publication helpers: finding fixed

Reviewed, without executing, these parent-owned temporary helpers:

- /tmp/nai-section-translation-baseline.py
- /tmp/nai-section-translation-build.py
- /tmp/nai-section-translation-stage.py
- /tmp/nai-section-translation-activate.py

The activation helper's original rollback() stopped and restarted the API when
modern_api_start_attempted was true but api_validated was false. Failure after
startup could therefore interrupt work accepted by that API. Reported this
directly to the parent; the parent moved the startup-attempt branch ahead of
service_touched recovery. Re-read the corrected function: after startup has
been attempted it retains the current process/release pointer and records
modern_advice_api_retained_forward_fix_required, with no second stop/start.
Baseline API recovery now occurs only before modern startup. Validated-API
web rollback also preserves that API. No live database restore is introduced.
The parent captured this boundary in backend/deployment-contract.md.

The helpers otherwise preserve explicit env-free locked build inputs, exact
working/committed/build file sets and hashes, immutable staged releases, pinned
CLI, side-effect-free schema checks, idle preflight, verified private online
SQLite backup, API-first switch, unchanged configuration/schema/record counts,
local private-image byte/expiry verification and retained old releases/assets.
Public checks are asset/readiness and unauthenticated 401/no-store checks;
they do not issue a model/provider request or token. Actual idle/backup/state/
image/publication results belong to the parent's later activation evidence.

## Verification performed

Commands ran from apps/api with the clean prefix below, preventing provider
credentials and env-file loading from entering checks:

```sh
env -i PATH="$PATH" HOME="$HOME" UV_NO_ENV_FILE=1 UV_PYTHON_DOWNLOADS=never uv --no-config ...
```

| Check | Actual result |
| --- | --- |
| sync --frozen --extra test --extra lint --offline | Pass; 24 installed packages checked |
| run --frozen --extra test --extra lint --offline python -m pytest -q | Pass; 699 tests, 2 dependency deprecation warnings, 34.98s |
| run --frozen --extra lint --offline ruff check src tests | Pass; all checks passed |
| lock --check --offline | Pass; 25 packages resolved |
| Web npm run lint | Pass; ESLint and tsc --noEmit |
| git diff --check | Pass |
| Existing test_openapi_contract_matches_snapshot_without_database_or_provider_calls | Pass in the full suite; exact serialized snapshot equality and no DB/image/provider side effects |
| OpenAPI/API models/runtime/dependency source diff review | Unchanged except codex_advice.py INSTRUCTIONS; snapshot and lock files have no diff |
| Python type checking | Not configured; not claimed |

The two warnings are existing Starlette/httpx and AnyIO alias deprecations,
not failing assertions. No backend test, lint or type failure needed a fix.

Parent-reported fresh isolated env-free locked 25-input production build passed;
reviewed section-translation-build-verification.md. Source map SHA-256:
6468740cc44026368e61e703d08f116831b57942c47bd1ea4234284c4ffa281f.
No product sources changed during this review, so no rebuild was required.

No frontend/helper/browser automated tests, live AI/advice/provider requests,
token issuance, .env.local reads, credential output, authenticated private-image
downloads, deployment or commits were performed by this reviewer.

## Findings not fixed / acceptance remaining

No unresolved product or publication-helper source finding remains. The main
session still owns staging/activation and actual production evidence. Desktop/
mobile interaction, keyboard/focus behavior and actual model explanation quality
remain operator acceptance; static review and fake tests do not establish those.
Keep the broader task in_progress.
