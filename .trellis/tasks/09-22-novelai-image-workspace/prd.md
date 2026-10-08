# NovelAI Image Workspace

## Goal

Deliver a browser-based workspace where a user can search and compose NovelAI
prompt tags, request AI guidance, generate images, and revisit saved generation
parameters without exposing paid service credentials to the browser.

## User Value

- Keep prompt authoring, parameter tuning, AI guidance, and image generation in
  one focused interface.
- Protect paid-service credentials by routing all external calls through the
  application backend.
- Find valid Danbooru tags quickly from Chinese or English concepts and insert
  selected results into the generation prompt.
- Revisit previous prompts and generation parameters without requiring stored
  copies of generated images.

## Confirmed Facts

- An incomplete API prototype was discarded on 2026-09-23 in favor of a
  clean-slate plan. The fresh backend now includes SQLite/authentication,
  parameter-only generation history, ephemeral results, a real NovelAI MCP
  adapter and a key-gated Codex advice runner. The frontend and deployment
  scaffolds now exist; production deployment has not been exercised.
- The application code will live in this repository as two independently
  deployable applications: a React/MobX web app and a FastAPI API app.
- The NovelAI Image MCP server is already deployed externally at
  `https://www.fsstudy.com.cn/novel-ai-v5` and requires authentication.
- The public NovelAI Image MCP v0.4.0 documentation describes Streamable HTTP
  transport at `/mcp` with Bearer authentication. The deployed service's
  non-billable schema probe succeeded at `/novel-ai-v5` instead; the
  `/novel-ai-v5/mcp` URL returned HTML.
- The MVP will use the public DanbooruSearch REST API at
  `https://sakizuki-danboorusearch.hf.space/api` as an external tag-search
  provider. It will not self-host DanbooruSearch.
- The MVP is intended for multiple users. A user must provide a token before
  using protected application capabilities.
- Each user receives an application access token. FastAPI validates that token
  and uses server-managed NovelAI MCP and Codex credentials for upstream calls.
- Application access tokens are created and distributed by an administrator;
  the MVP has no public registration flow.
- The MVP supports text-to-image generation only.
- Persist per-user generation inputs and parameters, not generated image files.
  Returned images are viewable and downloadable during the active result flow.
- Existing `.env.local` is an untracked operator draft, not a verified runtime
  configuration; no secret values are recorded in the planning artifacts.
- Parameter history does not expire automatically; users can delete individual
  history records.
- Tag discovery in the MVP uses `/search` only; related-tag and artist
  recommendations are deferred.
- Tag search includes NSFW results by default, without a user-facing NSFW
  filter or toggle.
- AI advice is a temporary, stateless, single-input/single-output interaction.
  It receives only text explicitly submitted from its own input field and does
  not automatically observe the generation prompt, parameters, or page state.
- Translation is deferred and is not part of the MVP.
- On a successful first token entry, the backend establishes a browser session
  in a cookie so returning users can resume without entering the token again.
- `/home/ubuntu/AiQQ` is available as the local reference implementation for a
  Python service using `openai-codex-sdk` and the Codex CLI/app-server with
  isolated runtime and work directories, bounded concurrency, timeouts,
  cancellation, structured output, and restricted tool access. It also uses
  local SQLite files; this product will use SQLite for its own data.
- On 2026-09-24 the operator accepted AiQQ-equivalent Codex isolation for
  advice: fresh isolated work/runtime directories, read-only sandbox, no
  network or approvals, named capability switches off, and fail-closed
  rejection of observed tool events. This is not a guarantee that every tool
  is unavailable before execution; do not present it as one.
- Local development runs Vite HTTPS and FastAPI directly. On the single
  production server, the existing host Nginx serves built web assets and
  proxies to one loopback-only FastAPI process managed by systemd. Docker,
  Kubernetes and K3s are not required.

## Scope Boundary

The parent remains in **planning**; the backend, web and deployment children have
begun implementation after review. No paid
provider calls have been made by automated tests. Keep `.env.local` private
and do not overwrite its secrets; the user has corrected its MCP base path
and set its HTTPS origin from AiQQ. Stale `NAI_DATABASE_URL` / `NAI_MEDIA_DIR`
settings are ignored, and `NAI_TOKEN_HASH_KEY` is no longer used. No Codex URL
is needed by default. Production serves the UI at `/novelai/` and browser API
at `/novelai/api/*` on `www.firesoul.cn`; the proxy forwards these requests to
the backend's unchanged `/api/*` routes. The origin contains no path.

## Requirements

### R0. Token-Gated Multi-User Access

- Require a user-supplied token before allowing image generation, AI advice, or
  future tag lookup.
- Issue distinct, revocable application access tokens; do not treat upstream
  NovelAI MCP or Codex credentials as user credentials.
- Provide an administrator command to create server-generated, uniformly
  random 256-bit tokens, display a new plaintext token once, list non-secret
  token metadata, and revoke a token. Never allow user-chosen token values;
  persist only each token's SHA-256 digest, never its plaintext. No additional
  token-hash key or corresponding environment variable is required.
- Exchange a valid token for a backend-managed browser session and set it in an
  `HttpOnly`, `Secure`, and appropriate `SameSite` cookie. The frontend must not
  store the raw token in JavaScript-readable cookies or Web Storage.
- Restore a valid session automatically from the cookie, expose a logout action,
  and return to token entry when the session is absent, expired, or revoked.
- Reject missing or invalid tokens with a stable authentication error.
- Keep tokens out of application logs, analytics, error payloads, and generated
  frontend bundles.

### R1. Web Workspace

- Use React, TypeScript, and MobX.
- Provide a work-focused image-generation interface for composing a positive
  prompt and negative prompt, editing supported generation parameters,
  submitting a request, observing progress/errors, and inspecting generated
  images.
- Make newly generated images available for immediate viewing and download
  together with the generation metadata needed to reproduce them. The history
  does not restore image downloads after reload; temporary result URLs expire
  after a short window or API restart.
- Let each authenticated user browse saved positive/negative prompts and
  generation settings, reuse them, and delete one parameter-history record at
  a time. Do not automatically purge history based on age.
- The browser must call only the local FastAPI API and must not receive NovelAI
  or Codex credentials.

### R2. FastAPI Aggregation Backend

- Use FastAPI with typed request/response models and generated OpenAPI output.
- Own validation, external-service authentication, timeout handling, error
  normalization, and response shaping at the backend boundary.
- Let authenticated, explicitly submitted generation and advice requests call
  the configured paid upstream services during normal operation. Automated
  tests must use fakes and must never call paid upstream services.
- Expose health/readiness endpoints suitable for systemd and operator monitoring.
- Never return service credentials or sensitive upstream error details to the
  browser.

### R3. NovelAI Generation

- Connect to the external NovelAI MCP over Streamable HTTP using a server-side
  Bearer token.
- Support the documented `generate_image` tool with this MVP input subset:
  positive prompt, negative prompt, model, width, height, steps, CFG scale,
  sampler, seed, sample count, and quality preset.
- Do not expose img2img, inpainting, multi-character positioning, Vibe transfer,
  reference-image workflows, or other image-upload controls in the MVP.
- Return generated image content and normalized metadata through the FastAPI
  contract without exposing the raw MCP protocol to the frontend.
- Persist each submitted generation's positive/negative prompts, validated
  generation settings, effective seed, creation time, and outcome under the
  requesting user's identity. Do not persist generated image bytes as history.
- Surface authentication, validation, timeout, balance, and upstream failures
  as user-actionable application errors.

### R4. AI Advice

- Provide a FastAPI endpoint backed by the Codex Python SDK/CLI app-server
  integration pattern used by AiQQ for prompt and generation-parameter advice.
  Reuse the implementation pattern, not the AiQQ service or its stored data.
- Adapt the AiQQ isolation pattern rather than copying its chat-bot-specific
  behavior: per-turn workspace isolation, bounded concurrency, timeout and
  cancellation, cleanup, explicit instructions, restricted capabilities, and
  schema-validated output.
- Use the AiQQ-equivalent restricted runtime accepted above. Do not authorize
  shell, filesystem, MCP, subagent or image-generation tool use in advice;
  reject observed tool events and never feed their output to the user. The
  operator accepts that post-event rejection is not pre-execution denial.
- Present exactly one advice input and one output area. Submit only when the user
  invokes the action; do not continuously observe or automatically attach the
  generation prompt, parameters, tag state, or other page content.
- Treat every advice request as an independent turn. Do not retain conversation
  history or create persistent Codex threads for advice.
- AI advice is display-only in the MVP and must not silently mutate the
  generation prompt or parameters.
- Codex must not independently generate an image or invoke the NovelAI service.

### R5. External Tag Search

- Integrate the public DanbooruSearch REST API through a typed FastAPI adapter;
  the browser must not call the Hugging Face service directly.
- Use `/search` for the MVP; do not offer `/related` or `/artists` recommendation
  features.
- Request search results with NSFW tags included; do not filter NSFW candidates
  at the backend or in the workspace, and do not add an NSFW setting.
- Support explicit Chinese and English tag searches and return normalized tag,
  Chinese name, category, safety marker, popularity count, score, and summary
  fields needed by the workspace.
- Let the user insert selected canonical English tags into the positive or
  negative prompt without treating search as general text translation.
- Keep the provider base URL and future API key configurable on the server.
- Send the provider's recommended client/site attribution headers and include
  the required visible link to the original DanbooruSearch service.
- Respect provider concurrency and rate limits, and map cold start, timeout,
  HTTP 429, validation, and unavailability failures to stable application
  errors with a retry path.
- Keep the provider behind an adapter so a different search service can replace
  it without changing the frontend contract.

### R6. Packaging and Deployment

- Keep the web and API applications in one repository but build and release
  them separately without containers.
- Route browser and API traffic through one origin in production so it does
  not depend on permissive CORS.
- Document local Vite/FastAPI startup and initial single-server deployment
  through host Nginx and a systemd-managed API. No Docker or cluster manifests
  are required.
- Persist generation-parameter history, token hashes, and session state in a
  private local SQLite file across restarts, and document backup and restore.
  Generated image bytes are not part of persistent deployment storage.
- Document HTTPS termination for the production origin, without requiring a
  particular domain name or certificate issuer in the repository.
- Keep credentials in server-side secrets or environment variables rather than
  frontend bundles or tracked configuration.
- Define health checks, graceful shutdown, and rollback-compatible versioned
  code and static-asset releases for the selected deployment target.

## Acceptance Criteria

- [ ] AC0: A user without a valid token cannot call protected API operations;
  authentication failures do not disclose the submitted token or protected
  service details.
- [ ] AC0.1: Successful token entry creates a secure backend-managed cookie
  session; a reload restores the session, logout clears it, and the raw token is
  absent from JavaScript-readable browser storage.
- [ ] AC0.2: An administrator can create and revoke independent user tokens;
  revoked tokens and their existing sessions stop authorizing protected calls,
  and stored records cannot reveal the original token.
- [ ] AC1: A user can open the web app, enter prompts and supported parameters,
  submit one generation request, see its state, and immediately view and
  download each returned image with its reproducibility metadata.
- [ ] AC1.1: Each submitted generation's positive/negative prompts, parameters,
  effective seed, time and outcome survive reload in that user's history;
  other users and revoked sessions cannot access the records. Images are not
  retained as persistent history for later viewing or downloading.
- [ ] AC1.2: A user can delete one parameter-history record without changing
  others; history is not automatically removed with age, and deletion never
  implies that generated image bytes are stored in the database.
- [ ] AC2: Browser network calls target only the FastAPI API; NovelAI and Codex
  credentials do not appear in frontend bundles, storage, logs, or responses.
- [ ] AC3: The API validates the request before invoking MCP and maps known MCP
  authentication, validation, timeout, balance, and service failures to stable
  typed errors rendered meaningfully by the web app.
- [ ] AC3.1: The generation form and API expose exactly the agreed text-to-image
  parameter subset and reject unsupported or out-of-range values before an
  upstream generation call.
- [ ] AC4: A user can explicitly submit one advice input and receive one output;
  a second submission has no retained conversation context, and the request does
  not contain unsubmitted prompt, parameter, tag, or page-state data.
- [ ] AC5: Codex execution is concurrency-bounded, cancellable, time-limited,
  isolated in a fresh work/runtime directory with AiQQ-equivalent restricted
  capabilities, rejects observed tool events, and is cleaned up after success,
  failure, cancellation, or shutdown. This does not assert zero-tool proof.
- [ ] AC6: A user can submit a Chinese or English concept, see normalized
  DanbooruSearch results, and insert a selected canonical tag into a generation
  prompt without the browser calling the provider directly.
- [ ] AC6.1: Search handles provider timeout, cold start, validation failure,
  HTTP 429, and unavailability without losing the current prompt, and the UI
  links to the original DanbooruSearch service.
- [ ] AC6.2: Relevant NSFW tag candidates remain visible in search results by
  default, with no NSFW filter or switch in the web UI.
- [ ] AC7: Local Vite and FastAPI run without containers; single-server
  production uses host Nginx for built web assets and a systemd-managed API.
  Production serves browser and API routes over one HTTPS origin
  without exposing upstream credentials, and SQLite parameter history survives
  restarts with documented backup/restore steps but no archived generated images.
- [ ] AC8: Backend automated checks cover request validation, upstream error
  mapping and Codex structured-output handling with deterministic fakes and
  no paid calls. The frontend is reviewed and can build/start without browser
  or frontend automated tests, as requested by the operator. Real authenticated
  user actions can still invoke the configured NovelAI and Codex services.

## Out of Scope

- Implementing, deploying, or populating the future external tag-query service.
- Reimplementing or deploying the existing NovelAI Image MCP server.
- Intentionally granting Codex shell, filesystem, MCP, subagent, or
  image-generation tool use for this product workflow.
- Native mobile or desktop applications.
- Public registration, password login, password recovery, social login, and an
  end-user account-management portal.
- Img2img, inpainting, masks, image uploads, multi-character positioning, Vibe
  transfer, and reference-image workflows.
- Translation of free text or prompt text.
- Self-hosting or modifying the DanbooruSearch application, BGE-M3 model, or its
  vector indexes.
- Related-tag and artist recommendations through DanbooruSearch `/related` and
  `/artists`.
- A configurable NSFW tag-search policy or NSFW filter toggle.
- Kubernetes/K3s manifests or cluster provisioning for the MVP.
- Automatic age-based expiration of saved generation history.
- Persistent storage or per-user history of generated image bytes.

## Technical Notes

- Public NovelAI documentation used during planning:
  `https://xinvxueyuan.github.io/NovelAI-Image-MCP/tools/index.html` and its
  `generate_image` / `suggest_tags` reference pages.
- `https://huggingface.co/spaces/SAkizuki/DanbooruSearch` was inspected as a
  candidate external tag-query provider. It is a GPL-3.0 application with REST
  (`/api/search`, `/api/related`, `/api/artists`, `/api/health`) and Streamable
  HTTP MCP interfaces. Its runtime loads BGE-M3 through sentence-transformers,
  four embedding matrices, and in-memory caches, so self-hosting it does not fit
  the current memory constraint.
- The DanbooruSearch public service explicitly permits private and public API or
  MCP integration. Public integrations must link to the original service; its
  API also recommends client/site attribution headers. The service may cold
  start after inactivity and currently announces forthcoming API-key and rate
  limits, including per-key daily/minute budgets and concurrency 1.
- DanbooruSearch uses the `ffdkj` SQLite database as an upstream input and adds
  LLM-produced semantic expansion plus BGE-M3 runtime semantic search. It is a
  strong fit for external tag discovery, but it is not a non-AI translation
  implementation.
- Live API checks on 2026-09-23 passed against the public REST service: health
  returned `loaded=true`; Chinese search for `蓝色长发` returned canonical tags
  including `blue_hair` and `long_hair`; related search for `serafuku` returned
  `school_uniform` and `sailor_collar`; an invalid `limit=0` returned the
  documented HTTP 422 validation shape. Warm calls completed in approximately
  0.69-0.99 seconds. English fuzzy search returned valid results but did not
  always rank the expected canonical tag first, so the UI must present results
  for user selection rather than silently applying the top hit.
- Official OpenAI Codex SDK documentation was checked on 2026-09-23; the
  agreed AiQQ-equivalent restricted configuration and event handling need
  offline validation. They do not prove an absolute no-tools guarantee.
  See `research/integration-interfaces.md`.
- Deferred translation findings are in `research/deferred-translation.md`.
- The current repository root is not initialized as a Git repository, so final
  source-control and release steps require a repository to be initialized or
  configured.
