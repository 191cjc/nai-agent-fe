# API Design

Use the parent's `../09-22-novelai-image-workspace/design.md` as the contract:
route table, authentication/cookie security, SQLite schema, ephemeral image
results, async generation state machine, provider fault mapping and runtime
isolation. This child implements only `apps/api` (plus contract fixtures).

Group code by auth, generations/storage, tag search, advice, provider clients,
configuration and DB migrations. Keep HTTP/SDK adapters behind injected
interfaces. Use one API process and bounded in-process job workers in the
single-server Nginx/systemd deployment; mark unfinished jobs with unknown outcome at
startup rather than silently resubmitting a paid request. Transient result
routes stream owner-scoped images from bounded memory and expire; never write
generated images to the database, data volume or history.

SQLite backups are operated by the deployment child; provide a safe online
backup path, health/readiness and a migration plan. Prefer additive migrations
so compatible API image rollbacks work. No image-file cleanup or media backup
is needed; an API restart intentionally discards transient image results.

## MCP Response Bounds Follow-up (2026-10-08)

Offline review reproduced two gaps in the existing response-limit contract:
MCP's fixed 64 KiB decoded chunk aggregation delays deadline checks on tiny
stream chunks, and HTTPX can decompress a response beyond the configured cap
before the adapter checks its length. Fix the response reader at the provider
boundary without changing routes, request models, error codes or paid-call
retry behavior.

Use raw transport chunks and bounded identity/gzip/deflate decoding, with a
monotonic deadline established before opening each MCP RPC response. Check
the deadline between received chunks and after EOF/decoding; HTTPX's connect
and read timeouts still govern an individual blocking network operation.
Do not claim a hard wall-clock interruption of a synchronous blocked read.

The tag adapter already implements bounded decoding. Factor the common reader
into a private backend module rather than duplicating that logic; adapters
retain their own response caps, deadlines and exception-to-public-error mapping.
Preserve tag-search wire behavior and its existing regression suite. Add fake
stream regressions proving early deadline/cap rejection and valid compressed
JSON/SSE parsing, including no repeated `tools/call` after an uncertain outcome.
