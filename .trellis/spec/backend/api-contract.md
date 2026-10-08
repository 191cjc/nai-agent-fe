# Browser API Contract

## Scope / Trigger

When changing `/api/*` routes or their typed request/response models in
`apps/api/src/novelai_api/app.py`, update the checked-in OpenAPI snapshot
and review how the web app consumes the change.

## Signatures

- `create_app(settings: Settings, database: Database | None = None, ...) -> FastAPI`
  creates the browser API; schema generation must not connect to a provider
  or create a SQLite database.
- `GET /api/generations/{job_id}` returns saved parameters and transient
  owner-only image URLs. `POST /api/generations` returns `202` with a job ID.
- `GET /api/generations?limit=&offset=` returns parameter-only history;
  `limit` defaults to 20 and accepts 1-100. `offset` starts at 0 and accepts
  JavaScript-safe nonnegative integers so `next_offset` remains usable beyond
  10,000 records.
- `POST /api/advice` has a typed suggestion response. A default runner is
  wired only when `NAI_CODEX_API_KEY` is configured; see
  [Codex Advice Runtime Contract](./codex-advice-contract.md).

## Contracts

- Browser and API share an HTTPS origin. Backend routes remain `/api/*`;
  production browsers use `/novelai/api/*` because the proxy strips
  `/novelai` before forwarding. `NAI_PUBLIC_ORIGIN` contains no route path.
- Errors use `ApiError(code: str, message: str, retryable: bool)`; return
  generic user-visible messages, never upstream credentials or responses.
- `apps/api/contracts/openapi.json` is a deterministic, credential-free
  snapshot, not evidence that unconfigured providers work. Model and sampler
  are provisional strings, not an invented choice enum.

## Validation & Error Matrix

| Case | Result |
| --- | --- |
| Missing/invalid browser session | `401` with `ApiError` |
| Mutating request with wrong/missing `Origin` | `403` with `ApiError` |
| Foreign/missing owner-scoped job or image | `404` with `ApiError` |
| Invalid request body or query | `422` with `ApiError` |
| History `limit` outside 1-100 or unsafe `offset` | `422` with `ApiError` |
| Missing image provider | `503 provider_unavailable` |
| Missing Codex runner | `503 advice_unavailable` |

Where applicable, also document `429` rate/queue limits and `502`/`504`
provider failures in route response metadata. A successful generation
submission does not mean the paid job succeeded.
The tag-search 429 response documents an optional `Retry-After` header; only
validated upstream rate-limit hints include it, while local `search_busy`
does not. The JSON `ApiError` shape is unchanged.

## Good / Base / Bad Cases

- Good: an authenticated owner polls a `202` job, receives parameter-only
  history, and accesses an image only while it remains in memory.
- Base: schema generation with fake settings produces no SQLite file and
  no network activity.
- Bad: a foreign user receives another user's job data or a configured
  MCP/Codex secret appears in `/openapi.json` or a test snapshot.

## Tests Required

- `apps/api/tests/test_api_contract.py` compares the deterministic snapshot
  to `create_app` OpenAPI, checks protected-path errors and verifies no
  credential URL/env value leaks.
- Keep integration tests on disposable SQLite and fake providers; automatic
  tests must not call paid services.

## Wrong vs Correct

- Wrong: document only successful responses or infer advice availability
  from its OpenAPI response model.
- Correct: annotate reachable error codes with `ApiError`; advice availability
  requires configured credentials and the pinned CLI, not merely a schema.
