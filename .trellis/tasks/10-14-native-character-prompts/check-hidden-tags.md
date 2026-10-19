# Individual Hidden Tags — Independent Review (2026-10-19)

## Result

GREEN for the current hidden-tags follow-up. No product defects were found and
no product/test files needed checker changes. Review covered both changed
packages, the curated check context, PRD/design/implementation artifacts,
hidden-tags-design.md and hidden-tags-review-matrix.md. Earlier shipped task
features were reviewed only at affected integration boundaries.

## Findings (fixed)

No product fixes required. One documentation inconsistency was reported to
the parent: section-assistant-contract.md still described comma-space append.
The parent updated it to the shared comma-plus-newline helper and linked the
comment contract. Parent owns executable specs and release artifacts.

## Findings (not fixed)

None requiring product or design changes.

The intended bounded behavior remains explicit: multiline expressions and
contexts where reflow would promote literal inline `//` are manual-only.
Hidden tags retain their original weight and disable weight controls until
restored. These are compatible with the agreed conservative editing contract.

## Source review

- `PromptEditor` remains controlled by the raw draft. Only manual edit opens
  its textarea. Explicit blur reflows safe tags; mounting/history reuse does
  not. Duplicate occurrences use raw spans. Hidden chips stay visible with
  labelled type=button hide/restore controls, pressed state and muted styling.
  Blur/toggle/weight expansion checks the raw3000 bound before a write and
  preserves original source on failure. Existing height/footer/focus guards
  remain intact.
- Browser/Python parsers statically agree on physical LF/CRLF/CR lines,
  space/tab-leading markers, escaped markers and URLs, contiguous active or
  hidden blocks, mapped occurrence indexes and manual-only expressions.
  UTF16/Python source offsets remain local; wire ranges use occurrence indexes.
  Exact decimal weights and neutral unwrapping retain the existing shared
  setters. Hidden/manual-only occurrences cannot become experiment dimensions.
- Tag insertion, assistant append and snapshot append share the comma/newline
  boundary. Snapshot imports still validate independent proposed copies before
  one commit; target identities, destination enabled state, duplicate tags,
  assistant revisions and incomplete-draft editing rules remain intact.
- Modern editor requests explicitly send strict `prompt_comments=true`.
  Absent/false API requests retain legacy parsing/projection and omit the false
  field from both dump methods. Raw style, negative and section source persist
  in existing private JSON; schema4 and metadata version1 remain unchanged.
  Saved browser metadata validation selects the saved flag before restoration;
  reuse copies raw source and a later explicit submission opts into new syntax.
- Comments compile independently within each enabled section. Effective shared
  and character fields match metadata exactly and are not compiled twice.
  Metadata-free fields compile at their effective accessors. Fully hidden
  people disappear only from the effective list, preserving the remaining
  person's source coordinates and native-model gate. Effective base nonblank
  and raw/effective lengths validate before seed/history/provider side effects.
- MCP keeps its explicit argument allowlist. Flat/manual/automatic paths use
  effective base/negative/characters; raw metadata, syntax flag and hidden source
  are never forwarded. No paid-call discovery, retry or billing changes were
  introduced.
- Modern zero omission runs within active source blocks and preserves hidden
  source, unselected duplicates, remaining source spans and effective separators.
  Empty-base checks count only active survivors and effective shared content.
  Raw style and effective combined length bounds remain conservative and lazy.
  Frozen flag mode is independent of plan versions1/2. Legacy grammar, definition
  byte preservation, canonical comparison scope and no-ordinal-replay behavior
  remain unchanged; changed flag or hidden source still conflicts.
- The reviewed OpenAPI delta is exactly the optional boolean
  `GenerationRequest.prompt_comments` with false default. No unexpected routes,
  migrations, dependencies, credentials or provider fields were added.

## Verification actually run

From `apps/api`:

```sh
uv sync --frozen --extra test --extra lint --offline
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --offline --extra test --extra lint python -m pytest -q
uv run --frozen --offline --extra lint ruff check src tests
uv lock --check --offline
```

- Frozen sync: pass, 24 packages checked.
- Full fake-only backend suite: **699 passed in 36.22 s**. Two dependency
  deprecation warnings (Starlette/httpx and anyio portal alias), no failures.
- Ruff: pass over src/tests.
- Offline lock consistency: pass.
- Exact reviewed OpenAPI snapshot and side-effect-free schema regression: pass
  in the full suite.
- Backend type checker: not configured; not claimed as passed.

Meaningful new regressions exercise strict flag/default omission, line compiler
golden cases, exact independent projections and coordinates, rejection before
side effects, actual fake MCP flat/manual/automatic payloads, raw history and
snapshot backup/restart, modern candidate rejection/zero omission/budgets,
legacy absent/v1/v2 frozen identity/restart without ordinal replay, and new run
failure continuation with frozen source/seed.

From `apps/web`, `npm run lint`: **pass** (ESLint and TypeScript noEmit).
Repository `git diff --check`: pass. No frontend/helper tests or browser
automation were created or run; browser/Python parity was reviewed statically.

## Release-helper review (read only)

Read `/tmp/nai-hidden-tags-build.py`, `-stage.py` and `-activate.py` without
executing them. They preserve explicit env-free inputs, committed/working/build
file-set and hash matching, offline locked installs, exact staged OpenAPI,
unchanged schema4, API-first publication, idle/private-online-backup/config
continuity, private retained-image byte/expiry checks and old public assets.
The recovery path keeps the modern API after its first start attempt so an
older API cannot misinterpret flagged saved requests. No automatic database
restore is present. Fresh baseline, actual build/commit/staging/publication
and their live gates remain the parent's responsibility.

No `.env.local`, configured secrets, live provider or paid endpoint was accessed.
No production mutations, commits, build or deployment were performed by this
reviewer. Operator desktop/mobile interaction and generated appearance remain
separate acceptance checks; this report does not claim them.
