# NovelAI Image Workspace — Technical Design

## Scope and boundaries

- The parent PRD is the authoritative product scope and acceptance checklist.
- `apps/web` is a React/TypeScript/MobX client served by Vite locally and by
  the existing host Nginx in production. `apps/api`
  is a FastAPI app with typed Pydantic contracts. The
  browser uses same-origin `/api/*` locally and `/novelai/api/*` in production;
  the proxy strips `/novelai` before forwarding to the backend's `/api/*`.
  No upstream URLs or service secrets are needed in its bundle.
- Local development runs Vite and one API process directly. Production runs
  one systemd-managed API process behind the host Nginx, which serves separately
  built web assets. SQLite lives in a private local file under
  `/var/lib/novelai`; version API code and web assets independently. Generated
  image bytes are transient result data, never part of persistent storage.
- External adapters own NovelAI MCP Streamable HTTP, DanbooruSearch REST, and
  a strictly restricted Codex SDK/CLI runtime. None is browser-accessible.
- In the running application, authenticated user-initiated generation and
  advice use their real configured upstream services. Automated tests inject
  fake adapters and cannot call paid upstream services.
- No K8s/K3s manifest, image upload, auto-translation, or tag recommendation
  adapter is included.

## Starting point and configuration

- There is no pre-existing application to migrate. The new `apps/api` is
  underway and publishes an offline-tested browser contract; `apps/web` is
  building against that contract. Provider model/sampler values remain
  provisional and must not be presented as a verified choice list.
- Configure SQLite with a private **file path** (default under the API data
  directory), not a connection URL or a database server. Ensure the directory
  is writable and excluded from source control; only the API user can read it.
- Backend secrets are upstream credentials for enabled features, not a
  token-hash key: server-generated 256-bit access tokens are stored as SHA-256
  digests and need no separate hashing secret. Codex authenticates via the
  installed SDK/CLI's supported mechanism; do not invent an HTTP base URL.
  No media directory or image backup is required.
- Treat the existing untracked `.env.local` as operator-owned; it still has
  preliminary PostgreSQL/media fields and must not be silently rewritten or
  used as proof of a working configuration.

## HTTP contract (version 1)

All `/api/*` responses are typed; errors use `{code, message, retryable}` with
stable codes and no upstream response bodies, prompt echoes, or secrets. Expose
OpenAPI and docs in a controlled way that does not reveal configured secrets.

| Route | Body/response | Access |
| --- | --- | --- |
| `GET /api/health/live` | process health | public |
| `GET /api/health/ready` | SQLite connection and writable data directory | public |
| `POST /api/auth/session` | `{token}` → cookie, non-secret current-user metadata | public, rate limited |
| `GET /api/auth/session` | current-user metadata | session |
| `DELETE /api/auth/session` | clear cookie and invalidate server-side session | session |
| `POST /api/generations` | validated text-to-image request → `{id, status}` (202) | session |
| `GET /api/generations/{id}` | job status, saved request parameters and transient result links while available | owner |
| `GET /api/generations` | paginated parameter-only history (including submitted attempts) | session |
| `GET /api/generation-results/{id}/images/{image_id}` | short-lived authenticated result/download, not history storage | owner while live |
| `DELETE /api/generations/{id}` | delete one saved parameter-history record | owner |
| `POST /api/tags/search` | `{query, limit}` → normalized candidate list | session |
| `POST /api/advice` | `{input}` → validated, display-only suggestion object | session |

Allow only the PRD's generation parameters; translate API names into MCP
`prompt`, `negative_prompt`, `model`, `width`, `height`, `steps`, `scale`,
`sampler`, `seed`, `n_samples`, and boolean `quality` (the documented tool's
quality-preset toggle). Validate dimensions as multiples of 64, steps 1–50,
CFG scale 0–20 and sample count 1–8. Choose documented model/sampler values
after a non-billable authorized tool-schema compatibility check; use a
configurable allowlist if the deployed service cannot expose them. Resolve a
random seed to an explicit nonzero value **before** invoking MCP so stored
request metadata can reproduce it; do not claim knowledge of per-image seed
derivation if the upstream doesn't supply it.

## Identity and browser security

- Admin-only CLI: `create`, `list`, `revoke` tokens. Creation generates a
  cryptographically random 256-bit opaque token, creates a separate user
  identity and token record, prints the plaintext token once, stores only its
  SHA-256 digest. User-chosen or low-entropy tokens are forbidden. Listing
  includes only ID, label, created/revoked
  timestamps and optional expiry. Revocation invalidates its sessions on their
  next request; user data stays private, not erased by revocation.
- Login exchanges the raw token for a random opaque session identifier; store
  only its hash and token/user references in SQLite. Use a 30-day fixed
  session expiry (no silent extension) and tokens that do not expire by default
  until admin revocation. These are design defaults, not third-party limits.
- Set an `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` host-only session cookie
  in production. No JavaScript-accessible raw token, session ID, or service
  secret; avoid sensitive logs, tracing and reflected error bodies. Clear the
  session on logout and on 401 in the client. Local development must verify
  browser behavior with a local HTTPS origin before accepting AC0.1.
- Restrict state-changing requests to the expected HTTPS origin via Origin /
  Fetch Metadata checks plus SameSite cookies; no permissive CORS. Authenticate
  and check ownership on every history/status/image/delete route. Disable
  caching for protected image and metadata responses, use safe content types
  and controlled `Content-Disposition`; transient image results never become
  static web-server assets.
- Rate limit token exchange, generation, and advice independently; return
  generic auth errors. A revoked token or expired/revoked session gets a stable
  401 (not a leaked ownership hint). Foreign image/generation IDs return 404.

## Generation and history lifecycle

- A local SQLite database stores users, access_tokens, browser_sessions and
  generation_jobs (owner, prompts, validated parameters, effective seed,
  status, timestamps, safe error code). No table or file stores generated
  image bytes. Migrations accompany schema changes; one API process controls
  writes, using WAL/busy timeout as appropriate for concurrent readers.
- The API admits a bounded number of outstanding jobs and processes calls
  within one API process with bounded concurrency (start with one generation
  at a time). A 202 ID lets the UI poll for queued/running/succeeded/failed
  states without keeping an HTTP request open through the remote generation.
  Do not auto-retry a possibly billable MCP call. On restart, unfinished jobs
  become failed with a generic "outcome unknown" error, never silently
  resubmitted; users can decide whether to try again.
- Take only validated MCP Image content blocks; enforce count, MIME/format and
  per-image/aggregate byte ceilings. Do not expose remote saved paths or raw
  text blocks. Retain resulting bytes only in bounded, per-user, in-process
  memory for immediate authenticated view/download, expire them after a short
  fixed window and discard on restart. Never write images to SQLite, disk,
  object storage, backup or browser Web Storage. Partially invalid results
  clear transient buffers and mark the job failed; never auto-retry a billable
  call. TTL and memory caps are operational settings, not indefinite storage.
- Paginate parameter-only history newest first, including each submitted
  request and its safe outcome. The per-user delete operation removes only
  that database record, leaves other records unchanged and never schedules
  age-based history purging. Backups may still contain deleted parameters
  until their own documented retention expires.
- Check writable database volume/capacity before accepting work. Include
  parameter round-trip, ephemeral image expiry and ownership tests.

## External adapters and error handling

- **NovelAI:** use a configured `/mcp` Streamable HTTP endpoint with server
  Bearer token, strict tool name, bounded connect/overall timeouts, and an
  adapter that converts known validation/authentication/insufficient-balance/
  timeout/service faults into safe API codes. Do not retry generation after
  an uncertain timeout. Use dependency injection and fake content blocks in
  automated tests. Verify the deployed tool schema before enabling generation.
- **DanbooruSearch:** backend-only `POST /api/search`; send client attribution,
  configurable site URL and future API key, explicitly `show_nsfw: true`.
  A single in-flight provider search for the single API process prevents
  concurrency overruns. Cap/validate query length and limit, normalize
  canonical English `tag`, optional Chinese name/category/NSFW/count/score/
  summary without inventing unavailable values. Map cold start, rate limit
  (including Retry-After), timeout and 422; provide retry without modifying
  prompt input. Visibly link to the original service in the web UI.
- **Codex advice:** follow AiQQ's Python `openai-codex-sdk` + Codex CLI
  app-server integration (rather than a bare HTTP chat request), after
  verifying the supported installed SDK/CLI versions and APIs. No product
  requirement for a custom Codex base URL or model override; use the SDK's
  supported default configuration and secure runtime authentication. Use a
  dedicated
  isolated scratch work/runtime directory per request, without inherited
  repository or user files or session reuse. Match AiQQ's read-only sandbox,
  no-network/no-approval configuration and named capability switches; do not
  enable MCP, search, shell, filesystem, image, plugin or subagent tools for
  advice. Enforce a separate concurrency semaphore,
  input/output caps, timeout, cancellation, child cleanup and schema-validated
  JSON. Send **only** the advice box's submitted text with fixed system
  instructions. Reject tool-call events and malformed outputs; advice is
  display-only. The operator explicitly accepted AiQQ-equivalent isolation on
  2026-09-24: observed tool events fail closed, but this is not a proof that
  every tool is denied before side effects. Do not claim absolute no-tools
  enforcement; test the configured switches and event handling offline.

## UI and operational shape

- MobX stores auth status, prompt draft, supported parameters, tag candidates,
  advice text/output, generation job status and paginated history separately.
  None of the auth token, advice input or generated image bytes goes into Web
  Storage. Explicit buttons insert chosen tags and request advice; advice
  never reads form state automatically. Show and download images only while
  the transient result is available; the history shows prompts and parameters,
  never image thumbnails. A history delete action removes only that record.
- Serve production UI `/novelai/` and browser API `/novelai/api/*` behind one
  HTTPS origin; the DB and API port remain private. Host deployment includes
  versioned code/assets, a server-only environment template, health checks and
  graceful shutdown. Local Vite exercises the same API contract.
- Use SQLite's backup API or an equivalent consistent snapshot, not a blind
  copy of a live WAL database. Include restore verification, disk monitoring
  and a reversible release procedure. Roll back an API release only with
  backward-compatible schema migrations; otherwise restore a known-good
  SQLite snapshot. Generated images are intentionally absent from backups.

## Delivery split and risk gates

- Backend owns auth, persistence, APIs and provider adapters; web owns UI and
  MobX state against the published API contract; deployment owns systemd,
  Nginx HTTPS, private data directories and restore verification. The parent task owns
  contract/acceptance integration and final review.
- Before claiming readiness: verify AiQQ-style SDK/CLI versions, restricted
  runtime configuration and fail-closed tool-event handling,
  probe the
  actual NovelAI `generate_image` schema without paying for generation, test
  cookie behavior on the chosen local origin, check parameter history and
  deletion under restart/failure, verify result image expiry without disk
  writes, and validate browser-to-API behavior with fake
  upstreams. Keep automated test credentials and endpoints isolated from paid
  providers; this does not disable real user-initiated generation or advice.
