# Validation record

## Backend implementation checks

Run in `apps/api`, using disposable databases/files, synthetic image fixtures,
fake providers, and no live credentials or private datasets:

```sh
uv sync --frozen --extra test --extra lint
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra test --extra lint python -m pytest -q
uv run --frozen --extra lint ruff check src tests
uv lock --check --offline
```

- Full suite: 982 passed in 96.10 seconds. Two existing Starlette/httpx
  deprecation warnings; no failing tests.
- New purge regressions: 10 cases passed in 2.73 seconds.
- Frozen dependency sync, Ruff, offline lock check, and API diff whitespace check
  passed. No backend source edits after those checks at implementation handoff.
- Reviewed OpenAPI changes: the cleanup response/route, additive purge/pending
  arrays on generation views, and restore's 409 error only.

## Frontend implementation checks

- In-worktree ESLint/TypeScript passed.
- Staged locked install, ESLint/TypeScript, clean-environment `/novelai/` build,
  and exact input file/content verification passed in
  `/tmp/nai-dataset-review-web-24f8vopu`. The final post-review build verifies all
  46 inputs against the workspace and contains 11 output files, 808013 bytes.
- Final commands in the env-file-free stage:

  ```sh
  env -i PATH="$PATH" NAI_WEB_BASE_PATH=/novelai/ npm run lint
  env -i PATH="$PATH" NAI_WEB_BASE_PATH=/novelai/ npm run build
  ```

  The existing Vite main-chunk size advisory remains; no build/check failures.

## Independent full-scope review

- Independent full-scope review completed across frontend/backend source, task
  artifacts, and owning specs; no real training/reference content or private
  databases inspected. All three findings below were fixed and independently
  read by the main agent; no unresolved findings remain.
- Found a concrete per-open lifecycle bug: keying the grid by set ID alone could
  retain hide-discarded/filter state and pending callbacks when reopening the same
  set. Checker added `selectionVersion` and a set-ID/version grid key. Main
  independently reviewed the small fix and confirmed the teardown/key behavior.
- Found a truthful-reporting bug: single-viewer purge counts treated pending
  physical cleanup as completed deletion. Checker separated complete/pending
  counts; main flagged and independently reviewed the matching current-image
  placeholder correction. Both now distinguish pending from completed removal.
- Final affected frontend static/build checks passed after all fixes. Backend
  files were not changed during independent review, so the full backend results
  remain current. Final root `git diff --check` passed.
- A late source trace found that history can resume a dataset job into
  `GenerationStore`; its hidden full-PNG result could survive cleanup in
  `SavedResultsStore` and reappear when closing the viewer. Checker added an
  AppStore-composed cleanup callback for matching terminal results and purged-slot
  filtering/revocation in that consumer. Main independently reviewed the callback,
  terminal/busy/active-job guards, epoch invalidation, and load filter. Final
  frontend lint/TypeScript/build and exact source-input verification passed after
  this fix; no API contract or approved scope changes.

## Verification limits

- No browser/frontend/helper automated tests under the current project contract.
- No paid provider probes or deployment-initiated real dataset cleanup. After the
  implementation review, the operator explicitly requested production deployment;
  schema-13/API-first publication and metadata-only preservation checks are
  recorded in `deployment.md`.
- Actual private-set interaction remains operator acceptance. Code-level deletion,
  retention/index/owner boundaries and failure/restart behavior use synthetic
  regressions; frontend behavior uses independent source review/static checks.
