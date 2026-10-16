# Check: NovelAI-aware Advice

Date: 2026-10-16. Independent `trellis-check` review. Result: GREEN.

## Findings (fixed)

None. No product corrections or new tests were needed.

## Findings (not fixed)

None in the scoped change. Actual model suggestion quality and browser
interaction remain operator acceptance; offline/static checks do not establish
canonical tag recognition or generation quality.

## Source review

- `codex_advice.py` changes only fixed `INSTRUCTIONS`. Advice explicitly
  targets NovelAI image prompts and relevant generation settings, prefers
  established English NovelAI/Danbooru-compatible tags, translates Chinese
  intent and allows short English descriptors without verification claims.
  Requested subject/meaning/section is preserved; section suggestions ask for
  directly usable tags without headings/Markdown/explanations. Settings
  explanations remain allowed.
- Strict outer JSON `suggestion` transport, untrusted-input/no-tools/no-image
  instructions, runtime isolation/configuration, credentials, SDK/CLI pins,
  capacity/deadlines, event rejection and child cleanup are unchanged. Existing
  advice/API fake regressions exercise these boundaries. No generation,
  account, billing, database, endpoint or OpenAPI changes.
- `SectionAssistant.tsx` resolves scope from typed target scope/section, never
  labels or person numbers. Nested `satisfies Record<...>` maps cover all
  11 destinations: style, negative, shared scene/other, and character
  character/upper_clothing/lower_clothing/action/tags/special/other. Shared
  other describes global composition; character other remains local.
- The visible editable consultation names NovelAI, the exact opening label,
  appropriate destination scope, English comma-separated tags and the
  opening section's text. Prefix remains complete and text truncation follows
  it within the existing 4000-character bound. No sibling sections, settings,
  images or history are added. Only explicit request sends the visible input;
  plain editable suggestions still require explicit append/replace to the
  captured stable target. Existing request/identity/abort/session guards,
  application validation and popover controls are unchanged.
- `App.tsx` changes only the unified advice explanation and placeholder.
  The left drawer still sends only its explicit consultation; no draft access
  or automatic request/application was introduced.
- Reviewed parent-owned fresh `/tmp/nai-novelai-advice-build.py`, `-stage.py`
  and `-activate.py` read-only. No release blockers found: exact committed/
  working/build input comparison, frozen offline dependencies, fresh baseline,
  unchanged schema4, private online backup, idle/rechecks, API-first readiness,
  configuration/private-image/expiry preservation, public hashes/old assets
  and compatible rollback remain present. Checks of the balance route are
  unauthenticated 401/no-store checks, not provider/account queries. The
  reviewer did not execute build, staging, publication or production probes.

## Verification

Backend commands used a clean `env -i` with only PATH/HOME plus
`UV_NO_ENV_FILE=1 UV_PYTHON_DOWNLOADS=never`; no provider credentials or
`.env.local` were loaded.

- `uv --no-config sync --frozen --offline --extra test --extra lint`: PASS.
- `uv --no-config run --frozen --offline --extra test --extra lint python -m pytest -q`:
  **639 passed** in 33.78s. Two existing Starlette/httpx/anyio deprecation
  warnings; no failures. Existing suite uses fake providers/disposable data.
- `uv --no-config run --frozen --offline --extra lint ruff check src tests`:
  PASS.
- `uv --no-config lock --check --offline`: PASS.
- OpenAPI: unchanged snapshot; full suite includes exact deterministic
  schema/no-database/no-provider-call regression. Snapshot SHA-256:
  `9312ec42258a35b66d20876bd56c8e46599840962ce8f6858c0d352a311c6eaa`.
- Backend type checker: not configured; no type-check pass claimed.
- Web `env -i PATH="$PATH" HOME="$HOME" npm run lint`: PASS
  (ESLint and `tsc --noEmit`).
- `python3 .trellis/scripts/task.py validate .trellis/tasks/10-14-native-character-prompts`:
  PASS, implement38/check40 entries.
- `git diff --check`: PASS.
- No new copy-literal/frontend/helper tests, browser automation or live
  advice/image/provider/account probes. Paid calls: **0**.

Reviewed product-source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `apps/api/src/novelai_api/codex_advice.py` | `b937310ed4a26d67fe99f52f70c03b0cf21755712362b47357b6ea1194efa876` |
| `apps/web/src/SectionAssistant.tsx` | `7df8d7e84eadeb3f2dfb5294d177e958eb9726b98d6e9003f0b070bf74ab23cd` |
| `apps/web/src/App.tsx` | `e9710eabdca2fdd3e5641557352326a5b6d6b8a2250c58ce89a71bb244b8e1d6` |

Parent owns fresh build/commit/release evidence; no product change requires a
checker-triggered rebuild. Executable advice/section-assistant contracts were
already synchronized by the parent and match the reviewed implementation.
