# Browser API Contract

## Scope / Trigger

When changing `/api/*` routes or their typed request/response models in
`apps/api/src/novelai_api/app.py`, update the checked-in OpenAPI snapshot
and review how the web app consumes the change.

## Signatures

- `create_app(settings: Settings, database: Database | None = None, ...) -> FastAPI`
  creates the browser API; schema generation must not connect to a provider
  or create a SQLite database.
- `GET /api/generations/{job_id}` returns saved parameters and seven-day
  owner-only image URLs. `POST /api/generations` returns `202` with a job ID.
- `GenerationView.provider_request: dict[str, Any] | None = None` adds the
  captured MCP `generate_image` arguments to generation and experiment-group
  details. `HistoryItem` and paginated generation history omit this field.
- `JobStore.record_provider_request(user_id, job_id, arguments) -> bool`
  persists the snapshot once for an owned running job;
  `provider_request(user_id, job_id) -> dict | None` reads it with owner scope.
- `GenerationManager.submit(user_id, request) -> str | None` raises
  `GenerationNotConfigured` only at the initial missing-executor guard;
  the route catches this type, not its general RuntimeError base class.
- `GET /api/health/ready` checks database readiness; it does not assert image
  or advice provider configuration, upstream credentials or successful paid output.
- GET `/api/account/balance` exposes only authenticated normalized image-service
  Anlas and actual successful-fetch time; see [Balance](./account-balance-contract.md).
  It is independent of generation acceptance and cannot classify request cost.
- `GET /api/generations?limit=&offset=` returns parameter-only history;
  `limit` defaults to 20 and accepts 1-100. `offset` starts at 0 and accepts
  JavaScript-safe nonnegative integers so `next_offset` remains usable beyond
  10,000 records.
- `GenerationRequest.experiment` optionally saves exact group metadata in
  settings_json; /api/style-experiments list/detail pages expose it only to
  its owner. Images use separate private seven-day files. See
  [Image Retention](./image-retention-contract.md) for signatures/bounds,
  exact refusal pairs, pagination and storage lifecycle.
- `/api/style-experiment-runs` creates and observes server-owned background
  runs; GET `/active`, GET `/{id}` and POST `/{id}/stop` are owner scoped.
  See [Durable Experiments](./durable-experiment-contract.md) for exact shapes,
  idempotency, failure continuation and migration3.
- `POST /api/dataset-runs` creates a fixed-style dataset run of the same
  durable kind; reads/Stop use the style run routes. See
  [Dataset Runs and Export](./dataset-run-contract.md).
- `DELETE /api/style-experiments/{experiment_id}/discarded-images` permanently
  cleans discarded images of the current owner dataset. Generation views add
  stable-index purge/pending metadata; restoring a purged index returns 409.
  See [Dataset Review and Cleanup](./dataset-review-contract.md) for exact
  aggregate results, partial-failure retry and image-serving gates.
- `POST /api/advice` has a typed suggestion response. A default runner is
  wired only when `NAI_CODEX_API_KEY` is configured. Optional endpoint/model
  settings remain backend-only and do not change the browser schema; see
  [Codex Advice Runtime Contract](./codex-advice-contract.md).
- `/api/prompt-snapshots` lists/creates durable private named section bundles;
  `/{id}` reads/deletes only the owner's object. GenerationRequest adds optional
  validated prompt_sections metadata while retaining effective provider fields.
  See [Prompt Sections and Snapshots](./prompt-sections-contract.md) for exact
  types, exclusion of hidden text, idempotency, errors and schema4.

## Contracts

- Browser and API share an HTTPS origin. Backend routes remain `/api/*`;
  production browsers use `/novelai/api/*` because the proxy strips
  `/novelai` before forwarding. `NAI_PUBLIC_ORIGIN` contains no route path.
- Errors use `ApiError(code: str, message: str, retryable: bool)`; return
  generic user-visible messages, never upstream credentials or responses.
- Keep the full workspace input in `parameters`, including comments, section
  metadata and hidden source text. Capture `provider_request` at the adapter's
  submission boundary after schema validation and before its sole paid call;
  it contains exactly the allowlisted tool arguments, including the effective
  seed and capability-dependent position fields. Never include authentication
  headers, credentials, editor metadata or hidden text in this snapshot.
  Recording failure aborts before the paid call. A stored snapshot describes
  attempted submission, not proof of delivery, payment or successful output.
  It is the configured MCP service's input, not that service's internal
  downstream NovelAI HTTP body. Legacy/pre-submission records return null;
  never reconstruct an allegedly actual request from historical parameters.
  Snapshots survive restart, backup and image expiry until the job is deleted.
- Modern comment-aware MCP prompt strings are formatted as one line after
  filtering: physical CR/LF runs become a space in base/negative/character
  prompts before capture. `parameters` still returns raw workspace input;
  prior `provider_request` captures are immutable. Legacy absent/false comment
  mode and literal backslash-plus-n text remain unchanged. See
  [Individual Hidden Tags](./prompt-comments-contract.md) for exact rules.
- `apps/api/contracts/openapi.json` is a deterministic, credential-free
  snapshot, not evidence that unconfigured providers work. Model and sampler
  are provisional strings, not an invented choice enum. Character-bearing
  requests additionally validate the verified native model subset; see
  [Native Character Prompt Contract](./native-character-contract.md) for
  additive style/character fields, history defaults and API-first rollout.
- POST `/api/generations` returning the explicit pair
  `503/provider_unavailable` is a refusal before seed assignment, history
  creation, enqueue and provider invocation. Browser submission handling may
  safely distinguish that exact response from unknown transport/5xx outcomes.
  Enforce this with a dedicated not-configured exception at the initial
  missing-executor guard, caught specifically by the route. Never catch all
  RuntimeErrors here: history creation/executor submission may fail after
  persistence or queue insertion. Keep terminal job errors and other routes'
  provider errors separate. Deploy this backend correction before a frontend
  that treats the pair as definite refusal; retain it after a web rollback
  because already-open tabs may keep the new classification.

## Validation & Error Matrix

| Case | Result |
| --- | --- |
| Missing/invalid browser session | `401` with `ApiError` |
| Mutating request with wrong/missing `Origin` | `403` with `ApiError` |
| Foreign/missing owner-scoped job or image | `404` with `ApiError` |
| Invalid request body or query | `422` with `ApiError` |
| History `limit` outside 1-100 or unsafe `offset` | `422` with `ApiError` |
| Missing image provider | `503 provider_unavailable` |
| Other RuntimeError during history/executor submission | Generic server failure; acceptance remains unknown, never the explicit configuration refusal |
| Insufficient private image storage before paid admission | 503/result_storage_unavailable, no seed/history/provider work |
| Duplicate experiment ordinal or inconsistent total | 409/experiment_conflict before paid work |
| Missing Codex runner | `503 advice_unavailable` |
| Legacy job, discovery rejection or recording failure | Detail `provider_request` is null; no fabricated snapshot |
| Unknown paid outcome after capture | Retain exact attempted arguments; no automatic paid retry |
| Duplicate or foreign snapshot write | Refuse without overwriting or leaking another owner's data |

Where applicable, also document `429` rate/queue limits and `502`/`504`
provider failures in route response metadata. A successful generation
submission does not mean the paid job succeeded.
The tag-search 429 response documents an optional `Retry-After` header; only
validated upstream rate-limit hints include it, while local `search_busy`
does not. The JSON `ApiError` shape is unchanged.

## Good / Base / Bad Cases

- Good: an authenticated owner polls a `202` job, receives parameter-only
  history, and accesses a private retained image during its seven-day lifetime.
- Base: schema generation with fake settings produces no SQLite file and
  no network activity.
- Good: current/saved image details show complete private workspace inputs
  beside exact submitted MCP arguments; hidden comments appear only in the
  workspace input. Base: old history explicitly reports no captured request.
- Good: missing image executor causes generation POST to refuse with
  `503/provider_unavailable` before any seed, history or provider work. Base:
  database readiness may still return `200/status=ok` with no executor.
- Bad: a foreign user receives another user's job data or a configured
  MCP/Codex secret appears in `/openapi.json` or a test snapshot.

## Tests Required

- `apps/api/tests/test_api_contract.py` compares the deterministic snapshot
  to `create_app` OpenAPI, checks protected-path errors and verifies no
  credential URL/env value leaks.
- Keep integration tests on disposable SQLite and fake providers; automatic
  tests must not call paid services.
- `test_provider_requests.py` verifies committed snapshot equality at the fake
  HTTP boundary for flat/manual/automatic/all-hidden/legacy-schema requests,
  uncertain outcomes, pre-call refusal, experiment groups, owner isolation,
  immutable writes, restart/backup and schema4-to5 preservation. Assert the
  detail field is absent from `HistoryItem` in the exact OpenAPI snapshot.
- Generation regressions must distinguish missing executor (503 with no
  seed/history/enqueue/provider work) from generic RuntimeError in history
  creation or executor submission (unknown server failure, never the explicit
  refusal). Preserve any already-created history for user review.

## Wrong vs Correct

- Wrong: document only successful responses or infer advice availability
  from its OpenAPI response model.
- Correct: annotate reachable error codes with `ApiError`; advice availability
  requires configured credentials and the pinned CLI, not merely a schema.
- Wrong: infer successful image generation from readiness, or equate an
  accepted job's terminal provider error with POST refusal.
- Correct: check provider configuration separately; preserve the refusal's
  pre-acceptance boundary when changing submit or enqueue behavior.
- Wrong: label a frontend projection or rebuilt historical payload as the
  actual provider input. Correct: display only the adapter-captured snapshot
  and explain null snapshots without inventing missing fields.
