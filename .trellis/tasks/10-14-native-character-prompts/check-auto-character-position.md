# Automatic Character Position: Independent Check

Date: 2026-10-16. Final application source status: **SOURCE FROZEN**.

## Findings (fixed)

- File: `apps/web/src/App.tsx:133`.
  Issue: the character-section hint always instructed users to drag numbered
  markers, although automatic mode deliberately hides those controls.
  Fix: describe choosing automatic arrangement or manual adjustment. This is
  presentation text only; generation and position state are unchanged.
  Final App.tsx SHA-256:
  `98da89e0fa07188ed15d5b85038bc16977c785b479abe064eeaaea64fc97a517`.
  Parent must replace the earlier web build with a fresh build containing this
  reviewed source; the prior build is superseded by this local fix.

## Findings (not fixed)

No remaining application-source, OpenAPI or deployment-helper defects were
identified within the approved scope. No interface or design changes are
recommended. Parent corrected stale current no-restart language in its owned
specs to reflect the operator's subsequent explicit restart authorization.

Real NovelAI placement appearance and desktop/mobile interaction remain
operator acceptance, not established by these offline/static checks.

## Review coverage

Read the saved full hook context, check.jsonl task context, PRD/design/plan,
new automatic-position design and fresh non-billable provider-schema artifact;
reviewed the full application/test/OpenAPI diff and applicable backend/frontend
indexes, quality checks and cross-layer contracts. Traced the affected owning
source paths and their unchanged callers, rather than relying only on added
assertions.

- `GenerationRequest` accepts only actual booleans for the new field and
  defaults omitted mode to false. Coordinate type/range validation, native
  model allowlist, base composition and field bounds remain intact. Automatic
  mode still validates and persists coordinates; only the MCP mapping omits
  them. Existing full-request settings_json serialization and model defaults
  preserve ordinary/native/legacy history, owner isolation, backup/restart and
  reuse with no SQL migration.
- MCP mapping preserves the exact eleven original fields with no characters,
  even when automatic mode is stored or advertised. With characters, verified
  boolean or nullable-anyOf support receives an explicit true/false. Automatic
  children omit both coordinate keys and preserve order, prompt, empty child
  negative and enabled=true; manual children preserve exact validated axes.
  Missing/unverified flag support keeps coordinate-only manual compatibility
  and rejects automatic mode before tools/call. Unknown validation constraints
  fail closed; annotations do not constrain accepted booleans. Fresh discovery
  occurs per operation, and uncertain paid responses never retry or fall back.
- Server run creation serializes an independent frozen request with mode,
  coordinates and settings; group derivation keeps them and the effective
  seed across failures and restart. Existing claims/cursors remain the paid
  ownership boundary. Same-id comparison adds only an absent false mode to a
  parsed comparison copy; it does not rewrite definition_json, discard unknown
  keys or change original plan-version1/2 rendering. Changed mode conflicts in
  both directions. Regression coverage includes absent/explicit versions and
  byte-identical legacy definition preservation.
- Web requestFromDraft retains mode and validates all submitted nonblank
  characters, while stable draft-only identities stay out of requests. Reuse
  defaults absent mode to manual, restores coordinates and generates fresh
  identities; reset restores false. The generic setField increments the draft
  revision, invalidating pending entry restoration even after mode is toggled
  back. Entry/session/logout/disposal guards remain intact. StyleRunStore
  snapshots copy the full request and character objects, so later draft-mode
  or coordinate changes cannot alter submitted server runs.
- CharacterPositions uses a labeled native selector. User mode changes release
  active capture before state update; an effect also clears stale drag on
  automatic mode or removed/reused identities. Pointer/keyboard handlers check
  current mode and stable identity. Manual bounds, aspect fallback, selection,
  keyboard increments, center reset and cleanup remain intact. Automatic mode
  hides manual controls without discarding draft coordinates or IDs; selector
  focus and ordinary form behavior remain native. PromptSummary is shared by
  current/history/saved/run views: true shows automatic placement, false/legacy
  shows manual axes. No separate summary or request-building path was missed.
- OpenAPI diff is solely the additive optional boolean/default-false request
  property, reused by existing request/history/run schemas. The exact snapshot
  and constructor side-effect/secret-absence regressions passed. No dependency,
  SQLite schema, configuration, auth or paid retry change was introduced.

## Verification

Executed from `apps/api`:

```sh
uv sync --frozen --offline --extra test --extra lint
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY UV_NO_ENV_FILE=1 uv run --frozen --offline --extra test --extra lint python -m pytest -q
uv run --frozen --offline --extra lint ruff check src tests
uv lock --check --offline
```

- Frozen offline sync: pass, 24 packages checked.
- Full backend tests: **462 passed in 22.90s**. Two dependency deprecation
  warnings from FastAPI/Starlette HTTPX and AnyIO integration; no failures.
- Ruff source/tests: pass.
- Offline lock consistency: pass, 25 packages resolved.
- Python type-check: not configured, not claimed as passed.
- `apps/web` `npm run lint`: pass (ESLint and TypeScript `tsc --noEmit`),
  including a successful repeat after the App.tsx text fix.
- `git diff --check`: pass after the local fix.
- Backend tests were not repeated for the subsequent text-only web change.

## Deployment helper source review

Read both prepared helpers in full without executing or testing them:

- `/tmp/nai-auto-character-stage.py` SHA-256:
  `a4c5519939595b57c9c8eccacc1f6aabe6817c12109de8b328d8040c245c27e0`.
- `/tmp/nai-auto-character-activate.py` SHA-256:
  `1ad5bab28af7bf357ebea37e1ad2abc40e22aa5bcffa81c7854f97497804aea2`.

No blockers found. Staging checks committed source/build hashes, immutable
release inputs, pinned/frozen offline dependencies, isolated construction and
schema3 probes, and baseline pointer/PID continuity. Activation checks idle
jobs/runs, a verified private online backup, schema3/integrity/record continuity,
configuration continuity and API readiness/exact running OpenAPI before web
publication. It preserves retained image state and old assets, and verifies
public hashes/readiness/neighboring health. Recovery retains the new API after
validation; before validation it also checks for automatic-mode job/run
snapshots before choosing a compatible API. It never restores the live DB.

Parent owns the fresh final build, commits, staging, production execution and
actual release verification. This reviewer made no production operations,
credential/.env.local reads, provider/advice calls, browser work, frontend or
helper automated tests, or git commits/push/amend. Source inspection does not
establish interactive behavior or real-provider appearance.
