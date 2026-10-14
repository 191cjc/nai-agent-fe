# Backend Verification

## Implemented Contract

- `GenerationRequest` adds optional `style_prompt` and ordered
  `character_prompts: [{prompt}]` fields. Existing callers and saved JSON
  default to empty style and no characters. Six characters and 3000 characters
  per caption are workspace limits, enforced before submission.
- The base prompt contains style/shared text only. Blank style preserves the
  original shared string exactly; nonblank style joins trimmed nonempty sections
  with `, `. The combined base must remain nonblank and at most 3000 characters.
- Native characters require the six reviewed V4/V4.5/V5 non-inpainting model IDs.
  Flat requests keep editable model IDs. The MCP payload preserves the old
  eleven fields when no characters are present.
- Ordered native captions map to independent objects with `prompt`, empty
  `negative_prompt`, centered `x = y = 0.5`, and `enabled = true`.
- The capability gate intentionally recognizes the deployed untyped
  `array<object>` shape, optionally wrapped in nullable `anyOf`. It ignores
  schema annotations and accepts integer `minItems`/`maxItems` bounds only when
  the requested count satisfies them. It rejects unknown validation keywords,
  constrained item schemas (including typed properties/required fields or
  `additionalProperties: false`), contradictory shapes and missing support.
  These fail as `unsupported_character_prompts` before `tools/call`; this is a
  conservative capability recognizer, not a general JSON Schema validator.
- Existing `settings_json` persistence stores complete structured input without
  a database migration. Owner-scoped history, restart, online backup/restore and
  reuse of both legacy and structured records are covered with disposable data.

## Checks Run

From `apps/api`:

```sh
uv sync --frozen --offline --extra test --extra lint
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --offline --extra test --extra lint python -m pytest -q
uv run --frozen --offline --extra lint ruff check src tests
uv lock --check --offline
```

All passed. Final full suite: **211 passed in 8.80 seconds**, with two dependency
deprecation warnings from Starlette/httpx and AnyIO. No Python type checker is
configured. Scoped `git diff --check` passed.

OpenAPI was regenerated deterministically using fake Settings, an absent
temporary SQLite path and no network. Reviewed changes are the new caption
model, the two optional request/history fields, and removing the shared
prompt's standalone minimum length because style can supply the base.
The full offline snapshot regression passed.

All provider interactions used `httpx.MockTransport` or injected fakes. No paid
provider calls, production/private configuration changes, deployments, frontend
automated tests or browser tests were performed by this backend implementation.
Real provider output remains an operator integration gate.
