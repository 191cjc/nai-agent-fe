# Execution plan

## Start gate

- [x] Operator approved task creation and planning.
- [x] Operator selected current-training-set cleanup scope.
- [x] Source/spec investigation and PRD convergence completed.
- [x] PRD, design, and spec/research manifests prepared.
- [x] Presented the final planning summary; operator approved implementation with “开始改动吧” (2026-11-07).
- [x] Activated the task after approval with `task.py start .trellis/tasks/11-07-dataset-review-cleanup`.

## Ordered implementation

1. Dispatch `trellis-implement` with the active task path first and curated
   native context (child-side loading fallback). Ownership: affected API/storage,
   web saved-review/export code, synthetic regression tests, OpenAPI snapshot.
   The worker must respect shared edits and the operator's training-data ban.
2. Add schema-13 purge metadata/migration/readiness and batched owner-scoped
   target selection, tombstone lookup, completion, and restore refusal. Preserve
   history, names, captions, references, snapshots, and retained image indexes.
3. Add per-image removal to the ResultStore protocol, memory cache, and disk
   store. Preserve sibling access, original retention, safe filesystem handling,
   retry after marker/unlink failures, and truthful removal outcomes.
4. Implement the current-set cleanup endpoint and typed summary. Gate originals,
   thumbnails, covers, and restore by durable tombstones; guard stale renders.
   Intentionally review/update browser client and OpenAPI contracts.
5. Move review mode into selection-owned state, open datasets in grid without a
   full-PNG fetch, enable hide-discarded initially, and add confirmed cleanup.
   Invalidate affected caches/metadata and update grid, export, quick picks,
   navigation, preload, and restore controls for purged indexes.
6. Add meaningful synthetic API/storage/migration regressions. No frontend/helper
   automated tests or browser automation under the current project contracts.
7. Dispatch `trellis-check` for independent full affected-source review and the
   required checks; fix findings without re-reading private operator data.
8. Update owning dataset/image-retention/viewer/API/database contracts and record
   actual checks and remaining operator interaction. Follow Trellis finish/commit
   requirements after the final quality gate. Do not deploy or run real cleanup.

## Verification commands and review

From `apps/api`:

```sh
uv sync --frozen --extra test --extra lint
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra test --extra lint python -m pytest -q
uv run --frozen --extra lint ruff check src tests
uv lock --check --offline
```

Run focused new discard/retention tests during implementation, followed by the
required offline full suite once. Review OpenAPI changes intentionally; schema
creation must create no real DB or storage files and make no provider calls.

From staged `apps/web` inputs excluding `.env*`, install using the frozen npm
lockfile, run `npm run lint`, and run `npm run build` under a clean process
environment. Do not load deployment credentials or publish `dist`.

Review both cover/browse entry paths, all-purged and mixed-image groups, manual
grid/single toggling, hidden/search/paged targets, repeat/cancel cleanup, pending
failure retry, viewer/cache URL disposal, concurrent restore/render, close/logout,
and retention/restart behavior. Interactive private-image validation remains the
operator's task.

## Risk and rollback checkpoints

- Before migration/storage edits, confirm additive schema and old-manifest rules.
- Before enabling UI cleanup, prove physical deletion and retained sibling access
  with synthetic disk files, including unlink failure and retry.
- Do not compact original indexes or fake successful cleanup when unlink fails.
- Preserve durable markers on failure. Product rollback cannot recover deleted
  images; an API rollback must still respect purge tombstones.
- Revisit planning only if evidence changes approved product scope/behavior.

## Verified implementation status

- Backend/frontend implementation complete; independent full-scope review passed,
  including matching-result cache invalidation in AppStore/GenerationStore.
- Full backend suite: 982 passed; frozen sync, Ruff and offline lock passed.
- Final staged frontend ESLint/TypeScript and env-free production build passed
  after all fixes; exact 46-input source match verified (11 outputs, 808013 bytes).
- Main independently reviewed the checker's per-open lifecycle and pending/completed purge-copy fixes.
- Executable specs updated; see `validation.md` for evidence and operator-interaction limits.
- Operator requested deployment after the final review. Work commit `8499310`
  was created and deployed API-first with schema-13 preservation checks; see
  `deployment.md`. Next: archive this completed task and record the session.
