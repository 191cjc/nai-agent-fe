# Viewer Cache: Independent Quality Gate

## Result

GREEN; no findings or source changes by the independent trellis-check agent.
Implementation is limited to apps/web/src/saved-results.ts. Parent synchronized
the frontend contracts and task context. Backend behavior/schema are unchanged.

## Reviewed Behavior

- Same- and cross-group A -> B -> A always reads current owner-scoped metadata
  and skips PNG downloads on a valid cache hit. Cached paths originate from
  authenticated validated PNG misses; errors/placeholders never enter the cache.
- Map-order LRU touches hits and enforces both 32-entry and 64-MiB Blob.size
  limits. The current cached URL counts; one oversized image is transient.
- Cache expiry cannot extend the original server lifetime. Access pruning,
  request-crossing expiry and metadata shortening were reviewed.
- Cache/transient ownership, eviction, close/replacement, reset/logout start,
  failed logout, 401/dispose and late read guards release URLs safely and cannot
  refill a later session. Normal generation URLs remain separately owned.
- Image/index/parameters/filename/download and live comparison ordering remain
  aligned. No draft mutation, paid retry, Stop or provider change is introduced.
- Full affected frontend interfaces were reviewed across API, App, stores,
  style runs and retained viewing, beyond the changed cache methods.

## Verification

- Implementer and independent checker: npm run lint (ESLint + tsc --noEmit)
  passed; git diff --check passed.
- Independent read-only review/AST parsing of /tmp/nai-viewer-cache-build.py
  and /tmp/nai-viewer-cache-publish.py passed: explicit env-free locked build,
  committed source/dist/hash checks, web-only atomic release/fallback, exact
  public assets/health/old assets and unchanged API pointer/PID checks.
- Frozen saved-results.ts SHA256:
  1f8bc34666eb36dc8502aee78a1a34f1ec14f834a8f73354112e481166f777d8.
- No frontend/helper/browser automated tests or paid calls. No backend repeat
  was needed; its preceding combined release already passed 356 offline tests.
- Real desktop/mobile interaction remains operator acceptance; task in_progress.
