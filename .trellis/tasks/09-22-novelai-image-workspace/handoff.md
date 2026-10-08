# NovelAI Image Workspace — Handoff

Updated: 2026-10-08 (Asia/Shanghai)

## Current state

- The parent `09-22-novelai-image-workspace` remains **planning**. After the
  user approved implementation, `09-23-novelai-api` was started and is now
  **in_progress**. The published, offline-tested API contract was reviewed and
  `09-23-novelai-web` was activated on 2026-09-24. With both entry points
  present, `09-23-novelai-compose` was also activated; all three children are
  **in_progress**. The deployment child keeps its historical Compose slug but
  now implements a no-Docker host deployment. Web and deployment static
  reviews have completed; runtime release gates remain open.
- Per user request, the incomplete `apps/api` prototype (including tests,
  dependency lock, migrations, cache and venv) was removed. A fresh
  `apps/api` now contains a FastAPI app, versioned SQLite migrations,
  administrator token commands, secure cookie sessions, revocation, origin
  checks, parameter-only generation history, a bounded in-process job worker,
  short-lived owner-scoped PNG downloads, authenticated public tag search,
  and a real NovelAI Streamable HTTP MCP adapter. A Codex SDK/CLI advice runner
  is now wired when `NAI_CODEX_API_KEY` is configured. The most recent run passed
  **119 offline tests** against disposable SQLite files, fake providers and
  HTTP mock transports; regression checks cover automatic MCP wiring,
  OpenAPI credential isolation and DanbooruSearch's documented upstream
  `nsfw`/`final_score` response shape. A consistent SQLite online
  backup/restore test includes saved parameters but no image bytes. The web
  app and earlier Compose manifests existed before the operator chose host
  deployment. Historical automated tests never contacted
  paid services. The npm lockfile tarball URLs have since been switched from
  HTTP to HTTPS without changing their package pins or integrity hashes; a
  disposable offline API release install, pinned CLI path check, and Vite
  production build passed. A focused backend rerun passed 29 offline
  authentication/SQLite/history tests with paid credentials unset. The
  offline Python/npm lockfile checks and both
  Trellis context validations pass; offline Ruff is unavailable because its
  wheel is missing from the local cache (lint has not passed).
- The API now publishes `apps/api/contracts/openapi.json` for the dependent
  web child. Offline tests compare the snapshot to generated OpenAPI and
  verify normalized auth/CSRF/ownership/provider/validation errors without
  exposing credentials. This documents the current API, not proof that the
  configured Codex CLI or provisional generation model/sampler choices are
  production-ready.
- The history endpoint now accepts 1-100 records per page (20 by default)
  and permits offsets beyond 10,000 through the JavaScript-safe integer
  range. The web UI keeps its 20-record page size. The OpenAPI snapshot was
  updated statically; no tests or build ran after the operator's request.
- Codex advice now uses the AiQQ-pinned Python SDK and project-local CLI,
  private per-turn `CODEX_HOME` and work directories, isolated API-key login,
  structured output and post-event tool rejection. Offline tests cover
  cancellation, late tool events, secret isolation and child cleanup. The
  pinned CLI reports `unified_exec=true` even when configured `false`; the
  operator accepted this AiQQ-equivalent limitation, not an absolute
  pre-execution tools ban. No paid advice request has been made to verify a
  production model turn.
- Tag-search upstream responses are now streamed with a 1 MiB decoded cap and
  a 30-second overall deadline. Offline tests cover compressed responses,
  expansion bombs, malformed data, slow chunks and upstream 429 without
  buffering its body; valid upstream `Retry-After` seconds or HTTP dates are
  forwarded in the API's 429 response, while malformed values and locally busy
  responses omit the header. No automatic retry or live/paid call occurs in
  those tests.
- SQLite migration now creates new POSIX data directories/files with private
  modes and restricts existing DB/WAL/SHM files without modifying operator-
  owned directories. Backups use exclusive private creation and reject existing
  symlink destinations. Existing directory permissions and path-replacement
  races still require a trusted private deployment volume; Windows ACLs need
  separate review. This cannot reverse historical exposure.
- Trellis PRD, design, implementation plans, research and context manifests
  remain. The workspace is not a Git repository; do not `git init` as part of
  planning.
- The web frontend has a typed same-origin client, MobX workspace, transient
  generation gallery, parameter history, independent advice and tag search.
  The operator requested removal of frontend automated/browser tests and no
  further automated testing during frontend implementation. Frontend test
  files/dependencies and temporary local browser-preview artifacts were
  removed. A later `/novelai/` production build and frontend lint/typecheck
  passed; no frontend automated or browser tests ran. A subsequent dark
  NovelAI-inspired revision moved parameters to a left gear panel and history,
  tag search and advice to a collapsible bottom drawer. Web-only release
  `20260924T094207` introduced the dark layout; web-only release
  `20260924T095605` replaces free width/height inputs with a three-option
  preset selector, while preserving non-preset dimensions from saved history.
  Web-only release `20261008T025018` extends the selector to small, standard
  and large portrait/square/landscape groups (nine client presets). It is live
  with clean-source assets and matching browser theme color; the public page,
  asset, API health and `/aiqq/health` returned 200. The deployed MCP schema
  only accepts numeric dimensions; an authorized, non-billable schema query
  returned 401 on 2026-10-08, so these groups are not verified as V5's
  official sizes or billing tiers. Visual review remains open, and no paid
  generation or browser automation was run. The web lockfile's build-only
  `source-map-js` was subsequently updated from vulnerable `1.2.1` to `1.2.2`
  with an HTTPS mirror URL and upstream integrity hash; production runtime
  dependency audit had no findings before that update, and the full web
  dependency audit now also reports zero findings. `npm ci` and frontend
  lint/typecheck pass with the patched lockfile. The deployed web bundle was
  built before this build-only dependency update; no additional static release
  was necessary.
- The operator subsequently chose to remove Docker entirely: local development
  uses Vite/FastAPI; production is documented for host Nginx and systemd-managed
  FastAPI with private SQLite. The Compose, Caddy and Docker configuration files
  have been removed. The web
  build uses `/novelai/`; host Nginx maps `/novelai/api/*` to backend `/api/*`
  and retains hashed assets across static release switches. The systemd unit
  migrates before one worker starts, binds loopback, and uses a private state
  directory and root-only env file. On 2026-09-24, release
  `20260924T091327` was installed on the host serving `www.firesoul.cn`.
  The public `/novelai/` page, hashed asset, and API readiness route returned
  200 over HTTPS; `/aiqq/health` remained 200. The systemd API is active,
  SQLite and its directory are private, and an online backup restored into a
  disposable loopback-only API whose readiness passed. The drill instance was
  stopped and removed. No paid provider request or frontend/browser test was
  made. The root-only production env file was installed from the example with
  provider credentials blank; the operator must fill those privately. The
  restore drill did not verify owner-scoped history because its snapshot has no
  pre-existing test history or two retained owner tokens. One application
  test token was issued later; its plaintext was shown only to the operator.
  Off-host encrypted backups are not yet
  configured. The operator-owned env file is guarded against overwrite in
  the setup instructions. A host-local
  process able to call the loopback API directly can forge forwarding headers;
  the single-server deployment assumes trusted host-local workloads.
- `.env.example` now describes the SQLite-file configuration for the current
  API authentication foundation and future adapters.
  **The operator has corrected `.env.local`'s MCP URL to the deployed base
  path and set `NAI_PUBLIC_ORIGIN=https://www.firesoul.cn`, derived from
  AiQQ's default public base URL (`https://www.firesoul.cn/aiqq`).** The file
  still contains obsolete `NAI_DATABASE_URL`, `NAI_MEDIA_DIR` and
  `NAI_TOKEN_HASH_KEY` fields; `NAI_SQLITE_PATH` is absent, so the app uses
  the working-directory-relative default. The backend does not automatically
  read `.env.local`; inject the required settings into its process environment.
  The hashing key is no longer needed: only server-generated, uniformly
  random 256-bit user tokens and their SHA-256 digests are planned. The file
  is private operator input, not a validated deployment configuration. Never
  print or commit its secrets, and do not overwrite the file wholesale.
- The operator selected `/novelai/` UI and `/novelai/api/*` browser API on
  `www.firesoul.cn`, alongside the existing `/aiqq` route. Host Nginx owns
  TLS and static web assets, strips `/novelai` only for API forwarding to the
  loopback API, and replaces client-supplied forwarding IP headers.
  Keep paths out of `NAI_PUBLIC_ORIGIN`. Host deployment is in progress.

## Agreed MVP

- A React/TypeScript/MobX web workspace and FastAPI API, independently built
  and deployed behind one origin; local development uses Vite/FastAPI while
  single-server production uses host Nginx and systemd. Docker and K8s/K3s
  are not required.
- Admin-issued individual application access tokens; only token hashes are
  stored. Exchange a token for a revocable server-side session cookie. Require
  authentication for image generation, tag search and advice. No registration.
- Text-to-image via server-managed NovelAI Image MCP. Store each user's
  positive/negative prompt, generation settings, effective seed, timestamps
  and outcome in private local **SQLite**. Users can revisit and individually
  delete parameter-history entries; do not store image bytes or thumbnails in
  SQLite, persistent volumes or backups. Bounded in-memory results can be
  viewed/downloaded briefly and expire or disappear on API restart.
- DanbooruSearch `/search` through FastAPI, including NSFW candidates by
  default. Users explicitly choose canonical tags for either prompt.
  Related-tag/artist recommendations and translation are out of scope.
- A separate single-input/single-output Codex advice action based on AiQQ's
  Python SDK + CLI/app-server pattern. Send only the explicitly submitted
  advice text; no page-state snooping, retained chat history or automatic image
  generation. No custom Codex base URL required by default. On 2026-09-24 the
  operator accepted AiQQ-equivalent restricted capabilities and fail-closed
  observed-tool rejection in place of a provable pre-execution all-tools ban.
- Automated tests inject fakes and never call paid providers. Authenticated
  actions in a running configured app may call paid providers normally.

## Starting point and gates

1. The backend child was activated after approval. Its image lifecycle is
   exercised with fakes and the real MCP adapter with mock transport;
   DanbooruSearch's source response schema is covered by offline fixtures,
   and its public REST health/search were probed during planning. The new
   adapter's normalized response has not been rechecked live. The agreed
   AiQQ-style Codex isolation is implemented and covered by historical offline
   tests; the web and host deployment consume the published API contract.
2. A non-billable authorized MCP `initialize` / `tools/list` probe succeeded
   at `https://www.fsstudy.com.cn/novel-ai-v5` (protocol `2025-06-18`), but
   `/novel-ai-v5/mcp` returned HTML. The deployed `generate_image` schema
   includes the planned arguments; `model` and `sampler` have no enums.
   **No paid generation probe has been made.** Static/offline Codex research
   in `../09-23-novelai-api/research/codex-tool-isolation.md` could not prove
   pre-execution denial of every tool. The operator made the alternative
   product/security decision on 2026-09-24: use AiQQ's restricted runtime
   and post-event blocking, acknowledging that it is not an absolute guarantee.
   Do not make billable model calls in automated tests.
3. The API uses SQLite from day one, with no PostgreSQL migration. Host
   deployment files replace Compose. Production proxy and service startup now
   pass basic HTTPS/readiness checks, as does an empty-database restore drill;
   owner-scoped restoration and off-host backup remain release gates. The
   operator requested no further automated/browser tests during frontend
   implementation.
4. Before release, validate multi-user isolation, revocation, non-expiring parameter history,
   record deletion, ephemeral results, restart recovery, cookie/TLS behavior,
   SQLite online backup/restore and same-origin deployment with fakes and
   disposable data. A failed/ambiguous paid request must never auto-retry.

## Open implementation decisions

- Confirm deployed MCP model/sampler choices, effective seed behavior and
  actual result payload before freezing UI options and image metadata; the
  deployed tool schema provides no model/sampler enums.
- Verify Codex authentication and a real model turn with operator-approved
  credentials before production use. Offline fakes cover JSON, restricted
  configuration, tool-event rejection and cleanup; read-only sandboxing does
  not prove all tools are disabled. The npm package mirror now uses HTTPS
  with the existing integrity hashes; verify any operator-supplied registry
  override is also HTTPS before production.
- Specify resource limits (image result TTL, memory cap, request size and
  per-provider concurrency) based on verified schema and available server
  capacity; the single-process transient-result design cannot scale to
  multiple workers without redesign.
- Initial testable API limits are a ten-minute result TTL, 64 MiB process
  result-cache ceiling, one running generation and two queued jobs. Review
  these against real image sizes before using the paid provider in production.
- The production origin and path are chosen: `https://www.firesoul.cn`,
  `/novelai/` UI and `/novelai/api/*` browser API behind host Nginx. The
  Nginx-to-Uvicorn client-IP chain is documented but not runtime verified;
  it must not trust caller-supplied forwarding headers.
- Confirm the existing Nginx certificate/access policy, API secret delivery,
  package-source policy and SQLite backup retention before production use.

The current API configures the real NovelAI provider only when the server
receives an MCP token; without one, generation reports `503 provider_unavailable`.
With a corrected MCP URL/token, a user's authenticated generation may consume
paid NovelAI credits. Codex advice is available only with `NAI_CODEX_API_KEY`
and the installed pinned CLI; without the key it returns `503 advice_unavailable`.
Authenticated tag search can call the public REST service in normal runtime.
Offline tests call neither live provider nor paid service. This is not a
complete product release.
